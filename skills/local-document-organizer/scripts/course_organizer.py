#!/usr/bin/env python3
"""Course adapter: reuse organizer classification and keep a durable local undo journal."""
from __future__ import annotations
import argparse
import os
import re
import sys
import uuid
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        break
from course_runtime import Config, CourseError, Run, Store, add_storage_args, cli_main, digest, emit, file_hash, read_json, require_approval, write_json
import local_document_organizer as baseline


def public_plan(plan: dict) -> dict:
    root = Path(plan["folder"])
    return {"plan_id": plan["run_id"], "plan_sha256": plan["plan_sha256"],
            "skipped": [{"source_ref": Path(s["path"]).relative_to(root).as_posix(), "reason": s["reason"]} for s in plan.get("skipped", [])],
            "actions": [{"source_ref": Path(s["old_path"]).relative_to(root).as_posix(),
                         "destination_ref": Path(s["new_path"]).relative_to(root).as_posix(),
                         "category": s["category"], "confidence": s["confidence"],
                         "sha256": s["sha256"], "size_bytes": s.get("size_bytes", 0)} for s in plan["suggestions"]]}


def checked_plan(path: Path, store: Store) -> dict:
    plan = read_json(path)
    if not isinstance(plan, dict):
        raise CourseError("INVALID_PLAN", "Use the JSON plan produced by scan, not a list or another file.")
    signature = plan.pop("plan_sha256", None)
    if not signature or digest(plan) != signature:
        raise CourseError("PLAN_CHANGED", "Plan content changed after preview; scan again.")
    plan["plan_sha256"] = signature
    if (not isinstance(plan.get("run_id"), str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", plan["run_id"])
            or not isinstance(plan.get("folder"), str) or not plan["folder"]
            or not isinstance(plan.get("suggestions"), list) or not isinstance(plan.get("skipped", []), list)):
        raise CourseError("INVALID_PLAN", "Plan metadata is incomplete; scan the source folder again.")
    if plan.get("scope") != list(store.scope):
        raise CourseError("SCOPE_MISMATCH", "Plan belongs to another organization/workspace.")
    root = Path(plan["folder"])
    safe, _ = baseline.is_safe_target(root)
    if not safe or not root.is_absolute() or root.resolve() != root or root.is_symlink():
        raise CourseError("UNSAFE_PATH", "Organizer target is unsafe.")
    for item in plan.get("skipped", []):
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k] for k in ("path", "reason")):
            raise CourseError("INVALID_PLAN", "Skipped-file entries require path and reason strings.")
        if Path(item["path"]).parent != root:
            raise CourseError("UNSAFE_PATH", "Skipped-file evidence must belong to the selected folder.")
    for s in plan["suggestions"]:
        if (not isinstance(s, dict) or not all(isinstance(s.get(k), str) and s[k] for k in ("old_path", "new_path", "category", "confidence", "sha256"))
                or not re.fullmatch(r"[0-9a-f]{64}", s["sha256"])
                or type(s.get("size_bytes", 0)) is not int or s.get("size_bytes", 0) < 0):
            raise CourseError("INVALID_PLAN", "Every proposed move needs complete source, destination and file evidence.")
        old, new = Path(s["old_path"]), Path(s["new_path"])
        if old.parent != root or not new.resolve().is_relative_to(root) or new.parent == root or old.is_symlink() or new.is_symlink():
            raise CourseError("UNSAFE_PATH", "Plan contains an out-of-folder action or symlink.")
        if new.parent.exists() and new.parent.resolve() != new.parent:
            raise CourseError("UNSAFE_PATH", "Destination directory is a symlink.")
    return plan


def scan(a, store: Store):
    root = Path(a.folder).expanduser().resolve()
    safe, _ = baseline.is_safe_target(root)
    if not safe:
        raise CourseError("UNSAFE_PATH", "Name an existing non-system subfolder to organize.")
    plan = baseline.build_plan(root, baseline.load_rules(a.rules), include_low_confidence=a.include_low_confidence, include_hidden=False)
    plan["run_id"] = str(uuid.uuid4())
    plan["scope"] = list(store.scope)
    for s in plan["suggestions"]:
        if Path(s["old_path"]).is_symlink() or not Path(s["new_path"]).resolve().is_relative_to(root):
            raise CourseError("UNSAFE_PATH", "A rule or file points outside the selected folder.")
        s["sha256"] = file_hash(Path(s["old_path"]))
    plan["plan_sha256"] = digest(plan)
    preview = public_plan(plan)
    if a.dry_run:
        emit({"status": "preview", **preview})
        return
    run = Run(store, "local-document-organizer", "Preview local file organization")
    run.artifact("organization_plan", "Proposed relative file actions", preview)
    run.save("previewed")
    destination = store.root / "organizer" / (plan["run_id"] + "-plan.json")
    write_json(destination, plan)
    baseline.write_report(plan, destination.with_suffix(".md"))
    report = destination.with_suffix(".md")
    report.write_text(report.read_text().replace("undo --log <log.json>", "undo --log <log.json> --confirm UNDO"), encoding="utf-8")
    emit({"status": "previewed", "run_id": run.id, "plan": str(destination), "proposed_moves": len(plan["suggestions"]), "plan_sha256": plan["plan_sha256"]})


def apply(a, store: Store):
    plan = checked_plan(a.plan, store)
    if a.dry_run:
        emit({"status": "preview", **public_plan(plan)})
        return
    require_approval(a.confirm, "ORGANIZE")
    log = store.root / "organizer" / (plan["run_id"] + "-actions.json")
    if log.exists():
        raise CourseError("ALREADY_APPLIED", "This plan has a recovery journal. Inspect or undo it; never replay it blindly.")
    run = Run(store, "local-document-organizer", "Apply reviewed file organization")
    run.artifact("approved_plan", "Approved organization plan", public_plan(plan))
    run.save("running")  # Remote scope/write/readback must succeed BEFORE touching local files.
    journal = {"run_id": run.id, "plan_id": plan["run_id"], "scope": list(store.scope), "folder": plan["folder"], "actions": []}
    write_json(log, journal)
    for s in plan["suggestions"]:
        old, new = Path(s["old_path"]), Path(s["new_path"])
        action = {"old_path": str(old), "new_path": str(new), "sha256": s["sha256"], "status": "intent"}
        journal["actions"].append(action)
        write_json(log, journal)  # Intent exists before mutation, even on interruption.
        try:
            if not old.is_file() or old.is_symlink() or file_hash(old) != s["sha256"]:
                action["status"] = "changed_or_missing"
            elif os.path.lexists(new):
                action["status"] = "conflict"
            else:
                new.parent.mkdir(parents=True, exist_ok=True)
                # A hard link is an atomic no-clobber destination reservation on the same volume.
                # Removing the old directory entry completes the approved move; contents survive.
                os.link(old, new, follow_symlinks=False)
                old.unlink()
                action["status"] = "moved"
        except FileExistsError:
            action["status"] = "conflict"
        except OSError:
            action["status"] = "failed"
        write_json(log, journal)
    results = [{"source_ref": Path(x["old_path"]).relative_to(plan["folder"]).as_posix(),
                "destination_ref": Path(x["new_path"]).relative_to(plan["folder"]).as_posix(),
                "status": x["status"], "sha256": x["sha256"]} for x in journal["actions"]]
    run.artifact("action_log", "Local reversible actions", results)
    run.event("local_journal_saved", {"plan_id": plan["run_id"], "recovery_available": True})
    status = "succeeded" if all(x["status"] == "moved" for x in results) else "partial"
    try:
        run.save(status)
    except CourseError as exc:
        emit({"status": "local_actions_recorded_remote_unverified", "error": exc.code, "run_id": run.id, "journal": str(log), "next": "Do not reapply. Use undo with --storage local, or inspect the canonical run and reconcile."})
        return 2
    emit({"status": status, "run_id": run.id, "journal": str(log), "actions": results})
    return 1 if status == "partial" else 0


def undo(a, store: Store):
    journal = read_json(a.log)
    if journal.get("scope") != list(store.scope):
        raise CourseError("SCOPE_MISMATCH", "Undo journal belongs to another workspace.")
    root = Path(journal["folder"])
    safe, _ = baseline.is_safe_target(root)
    if not safe:
        raise CourseError("UNSAFE_PATH", "Unsafe recovery root.")
    for x in journal["actions"]:
        old, new = Path(x["old_path"]), Path(x["new_path"])
        if old.parent != root or not new.resolve().is_relative_to(root) or old.is_symlink() or new.is_symlink():
            raise CourseError("UNSAFE_PATH", "Unsafe undo journal path.")
    if a.dry_run:
        emit({"status": "preview", "actions": len(journal["actions"])})
        return
    require_approval(a.confirm, "UNDO")
    # Local recovery is deliberately possible even when the persistence API is unavailable.
    for x in reversed(journal["actions"]):
        if x.get("undo_status") == "restored":
            continue
        if x["status"] not in {"moved", "intent", "failed"}:
            continue
        old, new = Path(x["old_path"]), Path(x["new_path"])
        try:
            if not new.is_file() or file_hash(new) != x["sha256"]:
                x["undo_status"] = "changed_or_missing"
            elif os.path.lexists(old):
                if old.is_file() and os.path.samefile(old, new):
                    new.unlink()  # Interrupted move left both links; the original still exists.
                    x["undo_status"] = "restored"
                else:
                    x["undo_status"] = "conflict"
            else:
                os.link(new, old, follow_symlinks=False)
                new.unlink()
                x["undo_status"] = "restored"
        except OSError:
            x["undo_status"] = "failed"
        write_json(a.log, journal)
    run = Run(store, "local-document-organizer", "Undo approved local organization")
    run.event("undo", {"original_run_id": journal["run_id"], "results": [x.get("undo_status", "not_moved") for x in journal["actions"]]})
    status = "succeeded" if all(x.get("undo_status", "restored") == "restored" for x in journal["actions"]) else "partial"
    try:
        run.save(status)
    except CourseError as exc:
        emit({"status": "local_undo_recorded_remote_unverified", "error": exc.code, "journal": str(a.log)})
        return 2
    emit({"status": status, "run_id": run.id, "restored": sum(x.get("undo_status") == "restored" for x in journal["actions"]), "journal": str(a.log)})
    return 1 if status == "partial" else 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    sub = p.add_subparsers(dest="command", required=True)
    scan_p = sub.add_parser("scan")
    scan_p.add_argument("--folder", type=Path, required=True)
    scan_p.add_argument("--rules", type=Path, default=baseline.DEFAULT_RULES)
    scan_p.add_argument("--include-low-confidence", action="store_true")
    apply_p = sub.add_parser("apply")
    apply_p.add_argument("--plan", type=Path, required=True)
    apply_p.add_argument("--confirm")
    undo_p = sub.add_parser("undo")
    undo_p.add_argument("--log", type=Path, required=True)
    undo_p.add_argument("--confirm")
    sub.add_parser("runs")
    a = p.parse_args()
    store = Store(Config.from_args(a))
    if a.command == "runs":
        emit([r for r in store.list("skill_runs") if r["data"]["skill_name"] == "local-document-organizer"])
    else:
        return {"scan": scan, "apply": apply, "undo": undo}[a.command](a, store)


if __name__ == "__main__":
    cli_main(main)
