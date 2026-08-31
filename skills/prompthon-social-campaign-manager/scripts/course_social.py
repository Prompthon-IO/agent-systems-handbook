#!/usr/bin/env python3
"""Prepare an offline course campaign using existing canonical Social payload helpers."""
from __future__ import annotations
import argparse
import datetime as dt
import sys
import urllib.parse
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        break
else:
    raise SystemExit("Install the course foundation (PR #222) before running this lesson.")
from course_runtime import Config, CourseError, Run, Store, add_storage_args, cli_main, digest, emit, identifier, read_json, write_json
import manage_social_campaign as baseline


def date(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise CourseError("TIMEZONE_REQUIRED", "Campaign/post times need an explicit UTC offset.")
    return parsed


def compile_plan(store: Store, request: dict) -> dict:
    if not isinstance(request, dict):
        raise CourseError("INVALID_PLAN", "Campaign input must be a JSON object.")
    strategy_id = identifier(request.get("strategy_id"), "strategy id")
    strategy = store.get("content_strategies", strategy_id)
    topic_ids = {t["id"] for t in strategy["data"]["priority_topics"]}
    campaign, entries = request.get("campaign"), request.get("posts")
    if not isinstance(campaign, dict) or not all(isinstance(campaign.get(k), str) and campaign[k].strip() for k in ("topic", "brief", "startAt", "endAt")):
        raise CourseError("INVALID_PLAN", "Campaign needs topic, brief and offset-aware startAt/endAt.")
    start, end = date(campaign["startAt"]), date(campaign["endAt"])
    if end < start or not isinstance(entries, list) or not 1 <= len(entries) <= 12:
        raise CourseError("INVALID_PLAN", "Use an ordered date range and 1–12 reviewed posts.")
    posts, seen = [], set()
    for entry in entries:
        key = identifier(entry.get("key"), "post key")
        providers = entry.get("providers")
        if key in seen or entry.get("topic_id") not in topic_ids:
            raise CourseError("INVALID_PLAN", "Post keys must be unique and every post must link to a current strategy topic.")
        if not isinstance(providers, list) or not providers or len(set(providers)) != len(providers) or not set(providers) <= {"linkedin", "facebook"}:
            raise CourseError("INVALID_TARGET", "The initial course fixture supports explicit LinkedIn/Facebook provider IDs; never use unknown IDs that could trigger a server fallback to all channels.")
        if not all(isinstance(entry.get(k), str) and entry[k].strip() for k in ("title", "copy", "publishAt")) or not start <= date(entry["publishAt"]) <= end:
            raise CourseError("INVALID_PLAN", "Each post needs title, copy and a timestamp inside the campaign window.")
        if entry.get("media") or entry.get("mediaUrls") or entry.get("generatedMedia"):
            raise CourseError("MEDIA_REVIEW_REQUIRED", "This text-only classroom adapter does not silently attach media; use a separately reviewed canonical media workflow.")
        overrides = entry.get("providerCopy", {})
        if not isinstance(overrides, dict) or set(overrides) - set(providers) or not all(isinstance(v, str) and v.strip() for v in overrides.values()):
            raise CourseError("INVALID_PLAN", "Provider copy must explicitly target the selected providers.")
        seen.add(key)
        settings = {**baseline.build_plan_settings(entry), "approvalRequired": True}
        posts.append({"key": key, "topic_id": entry["topic_id"], "title": entry["title"], "copy": entry["copy"], "publishAt": entry["publishAt"],
                      "providers": providers, "settings": settings, "variantOverrides": baseline.build_variant_overrides(entry, settings)})
    origin = store.config.api_url.rstrip("/") if store.config.api_url else None
    if origin:
        url = urllib.parse.urlsplit(origin)
        if url.scheme != "https" or url.username or url.password or url.path or url.query or url.fragment:
            raise CourseError("INVALID_ORIGIN", "Browser execution requires an explicitly configured HTTPS course origin.")
    core = {"schema_version": 1, "mode": "classroom_demo_only", "origin": origin, "organization_id": store.config.organization, "workspace_id": store.config.workspace,
            "strategy_id": strategy_id, "strategy_revision": strategy["revision"], "campaign": {k: campaign[k] for k in ("topic", "brief", "startAt", "endAt")}, "posts": posts}
    return {**core, "plan_sha256": digest(core)}


def prepare(store: Store, request: dict) -> dict:
    plan = compile_plan(store, request)
    if store.config.dry_run:
        return {"status": "preview", "plan": plan, "canonical_social_objects_created": False}
    run = Run(store, "prompthon-social-campaign-manager", "Prepare a classroom campaign without scheduling or publishing")
    run.save("running")
    plan["prepared_run_id"] = run.id
    output = store.root / "social-previews" / (run.id + ".json")
    write_json(output, plan)
    run.artifact("social_campaign_preview", "Canonical Social payload preview", {"plan_sha256": plan["plan_sha256"], "strategy_id": plan["strategy_id"], "strategy_revision": plan["strategy_revision"], "posts": len(plan["posts"]), "canonical_social_objects_created": False}, source_ref=output.name)
    run.save("previewed")
    return {"status": "prepared", "run_id": run.id, "plan_file": str(output), "plan_sha256": plan["plan_sha256"], "strategy_id": plan["strategy_id"], "canonical_social_objects_created": False,
            "next": "Review the file. The browser adapter requires signed-in Host access plus a live isolated-demo capability from backend dependency #221. Do not use the legacy apply-plan shortcut."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    p.add_argument("--request", type=Path, required=True)
    a = p.parse_args()
    emit(prepare(Store(Config.from_args(a)), read_json(a.request)))


if __name__ == "__main__":
    cli_main(main)
