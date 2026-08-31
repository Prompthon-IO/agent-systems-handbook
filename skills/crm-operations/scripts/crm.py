#!/usr/bin/env python3
"""Resolve demo CRM entities, review a revision-bound plan and apply audited changes."""
from __future__ import annotations
import argparse
import datetime as dt
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        break
else:
    raise SystemExit("Install the course foundation (PR #222) before running this lesson.")
from course_runtime import Config, CourseError, Run, Store, add_storage_args, cli_main, digest, emit, identifier, now, read_json, require_approval

COLLECTION = {"contact": "crm_contacts", "deal": "crm_deals", "activity": "crm_activities", "task": "crm_tasks"}
FIELDS = {"contact": {"name", "email", "company"}, "deal": {"contact_id", "title", "stage", "value", "currency"},
          "activity": {"contact_id", "deal_id", "body", "occurred_on"}, "task": {"contact_id", "deal_id", "title", "due_date", "status"}}
STAGES = {"lead", "qualified", "proposal", "won", "lost"}


def demo_context(store: Store) -> dict:
    context = store.context()
    if context["environment"] != "demo":
        raise CourseError("DEMO_REQUIRED", "CRM course operations require a server-attested demo workspace, never customer production records.")
    return context


def validate_fields(store: Store, kind: str, data: dict) -> dict:
    if kind == "contact":
        if not isinstance(data.get("name"), str) or not data["name"].strip() or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", str(data.get("email", ""))):
            raise CourseError("INVALID_CONTACT", "Contact requires a name and valid synthetic email.")
        data["name"], data["email"] = data["name"].strip(), data["email"].strip().casefold()
    else:
        contact = store.get("crm_contacts", identifier(data.get("contact_id"), "contact id"))
        if data.get("deal_id"):
            deal = store.get("crm_deals", identifier(data["deal_id"], "deal id"))
            if deal["data"]["contact_id"] != contact["id"]:
                raise CourseError("ENTITY_MISMATCH", "Activity/task deal belongs to a different contact.")
        if kind in {"deal", "task"} and (not isinstance(data.get("title"), str) or not data["title"].strip()):
            raise CourseError("INVALID_ENTITY", "Deal/task needs a nonempty title.")
        if kind == "deal":
            if data.get("stage") not in STAGES or not re.fullmatch(r"[A-Z]{3}", str(data.get("currency", ""))):
                raise CourseError("INVALID_DEAL", "Use a known stage and explicit three-letter currency.")
            try:
                value = Decimal(str(data["value"]))
                if not value.is_finite() or value < 0:
                    raise ValueError()
                data["value"] = format(value, "f")
            except (ValueError, InvalidOperation, KeyError):
                raise CourseError("INVALID_DEAL", "Deal value must be a finite nonnegative decimal.") from None
        if kind == "activity":
            if not isinstance(data.get("body"), str) or not data["body"].strip() or len(data["body"]) > 4000:
                raise CourseError("INVALID_ACTIVITY", "Supply a synthetic activity note of 1–4000 characters.")
        if kind == "task":
            if data.get("status") not in {"open", "completed"}:
                raise CourseError("INVALID_TASK", "Task status must be open or completed.")
        if kind in {"activity", "task"}:
            field = "occurred_on" if kind == "activity" else "due_date"
            try:
                value = data.get(field)
                if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError()
                dt.date.fromisoformat(value)
            except ValueError:
                raise CourseError("INVALID_" + kind.upper(), f"{field} must be a real ISO date in YYYY-MM-DD format.") from None
    return data


def all_records(store: Store, kind: str) -> list[dict]:
    result = store.list(COLLECTION[kind], 500)
    if len(result) >= 500:
        raise CourseError("RESOLUTION_LIMIT", "The classroom resolver is bounded to fewer than 500 entities; use the production CRM's paginated resolver for larger data.")
    return result


def plan(store: Store, request: dict) -> dict:
    if not isinstance(request, dict):
        raise CourseError("INVALID_REQUEST", "Provide a JSON object with entity, match and patch.")
    demo_context(store)
    kind = request.get("entity")
    if not isinstance(kind, str) or kind not in COLLECTION or not isinstance(request.get("match"), dict) or not isinstance(request.get("patch"), dict):
        raise CourseError("INVALID_REQUEST", "Provide entity, match and patch; deletion and arbitrary table operations are unsupported.")
    match, patch = request["match"], request["patch"]
    if set(patch) - FIELDS[kind] or not patch:
        raise CourseError("INVALID_FIELDS", "Patch fields must belong to the selected business object; audit/system fields cannot be supplied.")
    records = all_records(store, kind)
    if "id" in match and len(match) == 1:
        key = identifier(match["id"], "entity id")
        candidates = [r for r in records if r["id"] == key]
        create_id = key
    elif kind == "contact" and set(match) == {"email"}:
        key = str(match["email"]).strip().casefold()
        candidates = [r for r in records if r["data"]["email"].casefold() == key]
        create_id = "contact-" + digest(key)[:24]
        if str(patch.get("email", key)).strip().casefold() != key:
            raise CourseError("ENTITY_MISMATCH", "Resolve by id before changing an email identity.")
        patch = {"email": key, **patch}
    elif kind == "deal" and set(match) == {"contact_id", "title"}:
        key = {"contact_id": match["contact_id"], "title": str(match["title"]).strip()}
        candidates = [r for r in records if all(r["data"].get(k) == v for k, v in key.items())]
        create_id = "deal-" + digest(key)[:24]
        if any(patch.get(k, v) != v for k, v in key.items()):
            raise CourseError("ENTITY_MISMATCH", "Resolve by id before changing the deal identity.")
        patch = {**key, **patch}
    else:
        raise CourseError("RESOLUTION_REQUIRED", "Match contact by email/id, deal by contact+title/id, and activity/task by explicit id.")
    if len(candidates) > 1:
        raise CourseError("AMBIGUOUS_ENTITY", "Multiple matches require manual resolution; do not merge or guess.")
    current = candidates[0] if candidates else None
    before = {k: v for k, v in current["data"].items() if k in FIELDS[kind]} if current else {}
    if kind == "deal" and current and patch.get("contact_id", before["contact_id"]) != before["contact_id"]:
        raise CourseError("ENTITY_MISMATCH", "Course operations cannot reassign an existing deal to another contact; use a separately reviewed owning-app workflow.")
    after = validate_fields(store, kind, {**before, **patch})
    if kind == "contact" and any(r["id"] != create_id and r["data"]["email"] == after["email"] for r in records):
        # A matched contact retains its stable id even after an approved identity update.
        other = [r for r in records if r["id"] != (current["id"] if current else create_id) and r["data"]["email"] == after["email"]]
        if other:
            raise CourseError("DUPLICATE_CONTACT", "Another contact owns this email; inspect both records before making changes.")
    high_impact = kind == "deal" and ((current is not None and before.get("stage") != after["stage"]) or (current is None and after["stage"] in {"won", "lost"}))
    value = {"entity": kind, "id": current["id"] if current else create_id, "action": "update" if current else "create", "expected_revision": current["revision"] if current else 0,
             "before": before, "after": after, "high_impact": high_impact, "scope": list(store.scope), "no_change": bool(current and before == after)}
    return {**value, "approval_sha256": digest(value)}


def apply(store: Store, request: dict, confirmation: str | None, high_impact_approval: bool = False) -> dict:
    proposed = plan(store, request)
    if store.config.dry_run:
        return {"status": "preview", **proposed}
    require_approval(confirmation, proposed["approval_sha256"])
    if proposed["high_impact"] and not high_impact_approval:
        raise CourseError("HIGH_IMPACT_APPROVAL_REQUIRED", "A stage or close change needs separate approval and --approve-high-impact.")
    if proposed["no_change"]:
        return {"status": "unchanged", "id": proposed["id"], "revision": proposed["expected_revision"]}
    collection = COLLECTION[proposed["entity"]]
    current = store.maybe_get(collection, proposed["id"])
    if (current["revision"] if current else 0) != proposed["expected_revision"]:
        raise CourseError("CONFLICT", "Entity changed after resolution; review a new plan.")
    history = current["data"].get("audit", []) if current else []
    if len(history) >= 100:
        raise CourseError("AUDIT_LIMIT", "The course record reached its bounded audit limit; preserve history and move this demo to a fresh workspace.")
    run = Run(store, "crm-operations", "Apply a reviewed demo CRM mutation")
    run.event("mutation_planned", {k: proposed[k] for k in ("entity", "id", "action", "expected_revision", "approval_sha256", "high_impact")})
    run.save("running")
    audit = {"run_id": run.id, "at": now(), "actor_id": store.context()["actor_id"], "action": proposed["action"], "before": proposed["before"], "after": proposed["after"], "approval_sha256": proposed["approval_sha256"]}
    # Audit is embedded in the SAME atomic entity write, not an easily lost follow-up request.
    rec = store.put(collection, proposed["id"], {**proposed["after"], "audit": [*history, audit]}, expected_revision=proposed["expected_revision"])
    run.artifact("crm_mutation", "Canonical entity and atomic audit", {"collection": collection, "id": rec["id"], "revision": rec["revision"]})
    run.save("succeeded")
    return {"status": "succeeded", "run_id": run.id, "collection": collection, "id": rec["id"], "revision": rec["revision"], "audit_entries": len(rec["data"]["audit"])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("plan", "apply"):
        s = sub.add_parser(name)
        s.add_argument("--request", type=Path, required=True)
        if name == "apply":
            s.add_argument("--confirm")
            s.add_argument("--approve-high-impact", action="store_true")
    for name in ("list", "show"):
        s = sub.add_parser(name)
        s.add_argument("entity", choices=COLLECTION)
        if name == "show":
            s.add_argument("id")
    a = p.parse_args()
    store = Store(Config.from_args(a))
    demo_context(store)
    if a.command == "plan":
        result = plan(store, read_json(a.request))
    elif a.command == "apply":
        result = apply(store, read_json(a.request), a.confirm, a.approve_high_impact)
    else:
        result = all_records(store, a.entity) if a.command == "list" else store.get(COLLECTION[a.entity], a.id)
    emit(result)


if __name__ == "__main__":
    cli_main(main)
