#!/usr/bin/env python3
"""Turn an explicit content brief into a versioned topic system and editorial calendar."""
from __future__ import annotations
import argparse
import datetime as dt
import sys
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        break
else:
    raise SystemExit("Install the course foundation (PR #222) before running this lesson.")
from course_runtime import Config, CourseError, Run, Store, add_storage_args, cli_main, digest, emit, identifier, read_json, require_approval, write_json


def compile_strategy(brief: dict) -> dict:
    if not isinstance(brief, dict) or not all(isinstance(brief.get(k), str) and brief[k].strip() for k in ("business_goal", "target_audience")):
        raise CourseError("INVALID_BRIEF", "Define the business goal and target audience before choosing topics.")
    pillars, topics = brief.get("content_pillars"), brief.get("topics")
    if not isinstance(pillars, list) or not 1 <= len(pillars) <= 6 or not all(isinstance(p, str) and p.strip() for p in pillars) or len(set(pillars)) != len(pillars):
        raise CourseError("INVALID_BRIEF", "Supply 1–6 distinct content pillars.")
    if not isinstance(topics, list) or not 2 <= len(topics) <= 40:
        raise CourseError("INVALID_BRIEF", "Supply 2–40 candidate topics; this organizer does not invent search volume or demand.")
    ranked, seen = [], set()
    for topic in topics:
        if not isinstance(topic, dict) or not all(isinstance(topic.get(k), str) and topic[k].strip() for k in ("id", "title", "pillar", "query")):
            raise CourseError("INVALID_TOPIC", "Each topic needs id, title, pillar and an audience question/query.")
        identifier(topic["id"], "topic id")
        if topic["id"] in seen or topic["pillar"] not in pillars or topic.get("intent") not in {"searchable", "shareable"}:
            raise CourseError("INVALID_TOPIC", "Use unique topic ids, known pillars and searchable/shareable intent.")
        if not all(type(topic.get(k)) is int and 1 <= topic[k] <= 5 for k in ("business_fit", "audience_value", "effort")):
            raise CourseError("INVALID_TOPIC", "Business fit, audience value and effort are explicit 1–5 planning judgments.")
        if not isinstance(topic.get("evidence_refs"), list) or not all(isinstance(ref, str) and ref for ref in topic["evidence_refs"]):
            raise CourseError("INVALID_TOPIC", "Provide evidence_refs, or an empty list to mark the topic hypothesis as unvalidated.")
        seen.add(topic["id"])
        ranked.append({**topic, "priority_score": 2 * topic["business_fit"] + 2 * topic["audience_value"] - topic["effort"],
                       "validation_status": "source_supplied_review_required" if topic["evidence_refs"] else "unvalidated_hypothesis"})
    if {t["intent"] for t in ranked} != {"searchable", "shareable"}:
        raise CourseError("INTENT_REQUIRED", "Include both searchable and shareable topics; their distribution is a deliberate strategy choice.")
    ranked.sort(key=lambda t: (-t["priority_score"], t["id"]))
    calendar_config = brief.get("calendar", {})
    weekdays = calendar_config.get("weekdays")
    if not isinstance(weekdays, list) or not weekdays or len(set(weekdays)) != len(weekdays) or not all(type(d) is int and 0 <= d <= 6 for d in weekdays):
        raise CourseError("INVALID_CALENDAR", "Choose distinct weekdays as Monday=0 through Sunday=6.")
    try:
        zone = ZoneInfo(calendar_config["timezone"])
        day = dt.date.fromisoformat(calendar_config["start_date"])
        hour = int(calendar_config.get("hour", 9))
        if not 0 <= hour <= 23:
            raise ValueError()
    except (KeyError, ValueError, ZoneInfoNotFoundError):
        raise CourseError("INVALID_CALENDAR", "Calendar needs ISO start_date, an installed IANA timezone and hour 0–23.") from None
    calendar, clusters = [], defaultdict(list)
    for topic in ranked:
        while day.weekday() not in weekdays:
            day += dt.timedelta(days=1)
        calendar.append({"topic_id": topic["id"], "title": topic["title"], "intent": topic["intent"], "publish_at": dt.datetime.combine(day, dt.time(hour), zone).isoformat(), "status": "planned_not_scheduled"})
        clusters[topic["pillar"]].append(topic["id"])
        day += dt.timedelta(days=1)
    return {"brief": brief, "business_goal": brief["business_goal"], "target_audience": brief["target_audience"], "content_pillars": pillars,
            "topic_clusters": dict(clusters), "priority_topics": ranked, "content_calendar": calendar,
            "scoring_method": "2*business_fit + 2*audience_value - effort; editorial judgment, not market measurement", "external_scheduling": False}


def preview(store: Store, strategy_id: str, brief: dict, expected_revision: int) -> dict:
    identifier(strategy_id, "strategy id")
    current = store.maybe_get("content_strategies", strategy_id)
    if (current["revision"] if current else 0) != expected_revision:
        raise CourseError("CONFLICT", "Read the current strategy and supply its revision before planning an update.")
    compiled = compile_strategy(brief)
    plan = {"strategy_id": strategy_id, "expected_revision": expected_revision, "scope": list(store.scope), **compiled}
    return {"status": "preview", "plan_sha256": digest(plan), **plan}


def save(store: Store, strategy_id: str, brief: dict, expected_revision: int, confirm: str | None) -> dict:
    plan = preview(store, strategy_id, brief, expected_revision)
    if store.config.dry_run:
        return plan
    require_approval(confirm, plan["plan_sha256"])
    run = Run(store, "content-strategy", "Plan or iterate a source-attributed content strategy")
    run.save("running")
    data = {k: v for k, v in plan.items() if k not in {"status", "expected_revision", "scope"}}
    data["last_run_id"] = run.id
    record = store.put("content_strategies", strategy_id, data, expected_revision=expected_revision)
    artifact = store.root / "strategies" / strategy_id / (str(record["revision"]) + ".json")
    write_json(artifact, record)
    run.artifact("content_strategy", "Versioned topic system and calendar", {"strategy_id": strategy_id, "revision": record["revision"], "topics": len(data["priority_topics"]), "external_scheduling": False})
    run.save("succeeded")
    return {"status": "succeeded", "run_id": run.id, "strategy_id": strategy_id, "revision": record["revision"], "artifact": str(artifact), "content_calendar": data["content_calendar"], "external_scheduling": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("preview", "save", "show"):
        s = sub.add_parser(name)
        s.add_argument("--strategy-id", default="workshop-strategy")
        if name != "show":
            s.add_argument("--brief", type=Path, required=True)
            s.add_argument("--expected-revision", type=int, default=0)
        if name == "save":
            s.add_argument("--confirm")
    a = p.parse_args()
    store = Store(Config.from_args(a))
    if a.command == "show":
        result = store.get("content_strategies", a.strategy_id)
    elif a.command == "preview":
        result = preview(store, a.strategy_id, read_json(a.brief), a.expected_revision)
    else:
        result = save(store, a.strategy_id, read_json(a.brief), a.expected_revision, a.confirm)
    emit(result)


if __name__ == "__main__":
    cli_main(main)
