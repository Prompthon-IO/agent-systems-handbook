#!/usr/bin/env python3
"""Preview-first local document organizer for the local-document-organizer skill.

Provides a small CLI for scanning a folder, classifying files into category
subfolders, writing a preview Markdown report and JSON plan, executing
confirmed moves with an action log, and reversing those moves with undo.
The script never deletes or overwrites files.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RULES = SKILL_DIR / "references" / "classification-rules.csv"
DEFAULT_STATE = Path(
    os.environ.get(
        "LOCAL_DOCUMENT_ORGANIZER_STATE",
        str(Path.home() / ".codex" / "state" / "local-document-organizer"),
    )
)

CONFIRM_WORD = "ORGANIZE"
UNKNOWN_CATEGORY = "Unknown"
CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


# ---------------------------------------------------------------------------
# Time + path helpers
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def expand_path(raw: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def ensure_state_dirs(state_dir: Path) -> dict[str, Path]:
    paths = {
        "root": state_dir,
        "reports": state_dir / "reports",
        "plans": state_dir / "plans",
        "logs": state_dir / "logs",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def readable_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


# ---------------------------------------------------------------------------
# Safety guards
# ---------------------------------------------------------------------------


REFUSED_TARGETS = {
    Path("/"),
    Path("/System"),
    Path("/Library"),
    Path("/Applications"),
    Path("/usr"),
    Path("/var"),
    Path("/etc"),
    Path("/private"),
    Path("/bin"),
    Path("/sbin"),
}


def refused_user_targets() -> set[Path]:
    home = Path.home()
    return {
        home,
        home / "Library",
        home / ".ssh",
        home / ".gnupg",
        home / ".aws",
    }


def is_safe_target(path: Path) -> tuple[bool, str | None]:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        return False, "folder does not exist"
    if not resolved.is_dir():
        return False, "target is not a directory"
    if resolved in REFUSED_TARGETS or resolved in refused_user_targets():
        return False, f"refused target: {resolved}"
    return True, None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


SCHEMA = """
CREATE TABLE IF NOT EXISTS organizer_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS file_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    old_path TEXT NOT NULL,
    new_path TEXT,
    action TEXT NOT NULL,
    confidence TEXT,
    FOREIGN KEY(run_id) REFERENCES organizer_runs(id)
);
"""


def open_db(state_dir: Path) -> sqlite3.Connection:
    state_dir.mkdir(parents=True, exist_ok=True)
    db_path = state_dir / "organizer.sqlite"
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def load_rules(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    enabled: list[dict[str, str]] = []
    for row in rows:
        flag = row.get("enabled", "").strip().lower()
        if flag in {"true", "yes", "1", "on"}:
            enabled.append(row)
    return enabled


def classify(path: Path, rules: list[dict[str, str]]) -> tuple[str, str, str | None]:
    """Return (category, confidence, rule_id) for a path.

    Rules are evaluated in CSV order; first match wins. Filename keyword rules
    should sit above extension rules to give "invoice.pdf" the Invoices
    category instead of the generic PDFs category.
    """

    name = path.name
    stem = path.stem.lower()
    ext = path.suffix.lower().lstrip(".")

    for rule in rules:
        match_type = rule.get("match_type", "").strip().lower()
        pattern = rule.get("pattern", "").strip()
        if not pattern:
            continue
        if match_type == "extension":
            extensions = {token.strip().lower() for token in pattern.split("|")}
            if ext and ext in extensions:
                return rule["category"], rule.get("confidence", "low").lower(), rule.get("rule_id")
        elif match_type == "filename_keyword":
            keywords = [token.strip().lower() for token in pattern.split("|") if token.strip()]
            if any(re.search(rf"(^|[^a-z0-9]){re.escape(kw)}([^a-z0-9]|$)", stem) for kw in keywords):
                return rule["category"], rule.get("confidence", "low").lower(), rule.get("rule_id")
    return UNKNOWN_CATEGORY, "low", None


# ---------------------------------------------------------------------------
# Plan building
# ---------------------------------------------------------------------------


def is_hidden(path: Path) -> bool:
    return path.name.startswith(".")


def already_in_category(path: Path, root: Path, categories: set[str]) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    parts = rel.parts
    return len(parts) >= 2 and parts[0] in categories


def build_plan(
    folder: Path,
    rules: list[dict[str, str]],
    *,
    include_low_confidence: bool,
    include_hidden: bool,
) -> dict[str, Any]:
    suggestions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    categories = {rule["category"] for rule in rules} | {UNKNOWN_CATEGORY}

    for child in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_file() or child.is_symlink():
            skipped.append({"path": str(child), "reason": "not a regular file"})
            continue
        if is_hidden(child) and not include_hidden:
            skipped.append({"path": str(child), "reason": "hidden file"})
            continue
        if already_in_category(child, folder, categories):
            skipped.append({"path": str(child), "reason": "already inside a category folder"})
            continue

        category, confidence, rule_id = classify(child, rules)
        target_dir = folder / category
        proposed_new_path = target_dir / child.name
        try:
            size = child.stat().st_size
        except (FileNotFoundError, PermissionError, OSError):
            size = 0

        eligible = confidence in {"high", "medium"} and category != UNKNOWN_CATEGORY
        if not eligible and not include_low_confidence:
            skipped.append(
                {
                    "path": str(child),
                    "category": category,
                    "confidence": confidence,
                    "rule_id": rule_id,
                    "size_bytes": size,
                    "reason": "low confidence; pass --include-low-confidence to include",
                }
            )
            continue

        suggestions.append(
            {
                "id": f"move-{len(suggestions) + 1}",
                "old_path": str(child),
                "new_path": str(proposed_new_path),
                "category": category,
                "confidence": confidence,
                "rule_id": rule_id,
                "size_bytes": size,
            }
        )

    rid = run_id()
    return {
        "run_id": rid,
        "created_at": utc_now_iso(),
        "folder": str(folder),
        "rules_file": "",
        "suggestions": suggestions,
        "skipped": skipped,
        "include_low_confidence": include_low_confidence,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def write_report(plan: dict[str, Any], report_path: Path) -> None:
    suggestions = plan["suggestions"]
    skipped = plan.get("skipped", [])
    by_category: dict[str, list[dict[str, Any]]] = {}
    for suggestion in suggestions:
        by_category.setdefault(suggestion["category"], []).append(suggestion)

    total_size = sum(int(item.get("size_bytes", 0)) for item in suggestions)

    lines = [
        f"# Local Document Organizer Preview",
        "",
        f"- Run: `{plan['run_id']}`",
        f"- Created: `{plan['created_at']}`",
        f"- Folder: `{plan['folder']}`",
        f"- Proposed moves: {len(suggestions)}",
        f"- Skipped: {len(skipped)}",
        f"- Total size to relocate: {readable_size(total_size)}",
        f"- Includes low-confidence: {'yes' if plan.get('include_low_confidence') else 'no'}",
        "",
        "## Proposed Structure",
        "",
    ]

    if by_category:
        for category in sorted(by_category):
            items = by_category[category]
            cat_size = sum(int(item.get("size_bytes", 0)) for item in items)
            lines.append(f"### {category} ({len(items)} files, {readable_size(cat_size)})")
            lines.append("")
            lines.append("| File | Confidence | Rule | Size |")
            lines.append("| --- | --- | --- | ---: |")
            for item in items:
                old_name = Path(item["old_path"]).name.replace("|", "\\|")
                rule = item.get("rule_id") or "-"
                lines.append(
                    f"| `{old_name}` | {item['confidence']} | {rule} | {readable_size(int(item.get('size_bytes', 0)))} |"
                )
            lines.append("")
    else:
        lines.append("_No proposed moves. Either the folder is already organized, the only matches were low-confidence, or no files matched any rule._")
        lines.append("")

    if skipped:
        lines.extend(["## Skipped", "", "| File | Reason |", "| --- | --- |"])
        for item in skipped:
            old_name = Path(item["path"]).name.replace("|", "\\|")
            reason = str(item.get("reason", "")).replace("|", "\\|")
            lines.append(f"| `{old_name}` | {reason} |")
        lines.append("")

    lines.extend(
        [
            "## Approval",
            "",
            f"Run `apply --plan <plan.json> --confirm {CONFIRM_WORD}` only after user approval.",
            "Add `--include-low-confidence` only when the user explicitly opts in.",
            "Run `undo --log <log.json>` to reverse any executed moves.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Move execution
# ---------------------------------------------------------------------------


def execute_moves(plan: dict[str, Any], db: sqlite3.Connection, run_pk: int) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for suggestion in plan.get("suggestions", []):
        old_path = Path(suggestion["old_path"])
        new_path = Path(suggestion["new_path"])
        record: dict[str, Any] = {
            "suggestion_id": suggestion.get("id"),
            "old_path": str(old_path),
            "new_path": str(new_path),
            "category": suggestion.get("category"),
            "confidence": suggestion.get("confidence"),
            "rule_id": suggestion.get("rule_id"),
            "status": "pending",
            "logged_at": utc_now_iso(),
        }
        try:
            if not old_path.exists():
                record["status"] = "missing"
                record["reason"] = "source path no longer exists"
            elif new_path.exists():
                record["status"] = "conflict"
                record["reason"] = "destination already exists; refusing to overwrite"
            else:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_path), str(new_path))
                record["status"] = "moved"
        except PermissionError as exc:
            record["status"] = "permission_error"
            record["reason"] = str(exc)
        except OSError as exc:
            record["status"] = "failed"
            record["reason"] = str(exc)

        db.execute(
            "INSERT INTO file_actions(run_id, old_path, new_path, action, confidence)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                run_pk,
                record["old_path"],
                record.get("new_path") if record["status"] == "moved" else None,
                record["status"],
                record.get("confidence"),
            ),
        )
        actions.append(record)
    db.commit()
    return actions


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def command_scan(args: argparse.Namespace) -> int:
    folder = expand_path(args.folder)
    safe, reason = is_safe_target(folder)
    if not safe:
        print(f"Refusing scan target: {reason}", file=sys.stderr)
        return 2

    rules = load_rules(args.rules)
    paths = ensure_state_dirs(args.state_dir)

    plan = build_plan(
        folder,
        rules,
        include_low_confidence=args.include_low_confidence,
        include_hidden=args.include_hidden,
    )
    plan["rules_file"] = str(args.rules)

    plan_path = paths["plans"] / f"{plan['run_id']}-plan.json"
    folder_slug = re.sub(r"[^a-z0-9]+", "-", folder.name.lower()).strip("-") or "folder"
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = paths["reports"] / f"{today}-{folder_slug}.md"
    plan["plan_path"] = str(plan_path)
    plan["report_path"] = str(report_path)

    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    write_report(plan, report_path)

    with open_db(args.state_dir) as db:
        db.execute(
            "INSERT INTO organizer_runs(folder_path, created_at, status) VALUES (?, ?, ?)",
            (str(folder), utc_now_iso(), "previewed"),
        )
        db.commit()

    print(f"report={report_path}")
    print(f"plan={plan_path}")
    print(f"proposed_moves={len(plan['suggestions'])}")
    print(f"skipped={len(plan['skipped'])}")
    return 0


def command_apply(args: argparse.Namespace) -> int:
    if args.confirm != CONFIRM_WORD:
        print(f"Refusing to apply without --confirm {CONFIRM_WORD}", file=sys.stderr)
        return 2

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    folder = expand_path(plan["folder"])
    safe, reason = is_safe_target(folder)
    if not safe:
        print(f"Refusing apply target: {reason}", file=sys.stderr)
        return 2

    paths = ensure_state_dirs(args.state_dir)
    log_path = paths["logs"] / f"{plan['run_id']}-actions.json"

    with open_db(args.state_dir) as db:
        cursor = db.execute(
            "INSERT INTO organizer_runs(folder_path, created_at, status) VALUES (?, ?, ?)",
            (str(folder), utc_now_iso(), "applying"),
        )
        run_pk = cursor.lastrowid
        db.commit()

        actions = execute_moves(plan, db, run_pk)

        moved = sum(1 for action in actions if action["status"] == "moved")
        conflicts = sum(1 for action in actions if action["status"] == "conflict")
        missing = sum(1 for action in actions if action["status"] == "missing")
        permission = sum(1 for action in actions if action["status"] == "permission_error")
        failed = sum(1 for action in actions if action["status"] == "failed")

        if moved == 0 and (conflicts or missing or permission or failed):
            status = "no_moves"
        elif missing or conflicts or permission or failed:
            status = "partial"
        else:
            status = "ok"
        db.execute("UPDATE organizer_runs SET status = ? WHERE id = ?", (status, run_pk))
        db.commit()

    log = {
        "run_id": plan["run_id"],
        "db_run_id": run_pk,
        "folder": str(folder),
        "created_at": utc_now_iso(),
        "actions": actions,
        "status": status,
    }
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")

    print(f"log={log_path}")
    print(f"status={status}")
    print(f"moved={moved}")
    print(f"conflicts={conflicts}")
    print(f"missing={missing}")
    print(f"permission_errors={permission}")
    print(f"failed={failed}")
    return 0


def command_undo(args: argparse.Namespace) -> int:
    log = json.loads(args.log.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    for action in log.get("actions", []):
        if action.get("status") != "moved" or not action.get("new_path"):
            continue
        source = Path(action["new_path"])
        destination = Path(action["old_path"])
        record: dict[str, Any] = {
            "old_path": str(destination),
            "new_path": str(source),
            "status": "pending",
        }
        try:
            if not source.exists():
                record["status"] = "skipped"
                record["reason"] = "moved file no longer exists at recorded location"
            elif destination.exists():
                record["status"] = "skipped"
                record["reason"] = "original path already contains a file; refusing to overwrite"
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(destination))
                record["status"] = "restored"
        except PermissionError as exc:
            record["status"] = "permission_error"
            record["reason"] = str(exc)
        except OSError as exc:
            record["status"] = "failed"
            record["reason"] = str(exc)
        results.append(record)

    print(f"restored={sum(1 for item in results if item['status'] == 'restored')}")
    print(f"skipped={sum(1 for item in results if item['status'] == 'skipped')}")
    print(f"permission_errors={sum(1 for item in results if item['status'] == 'permission_error')}")
    print(f"failed={sum(1 for item in results if item['status'] == 'failed')}")
    return 0


def command_runs(args: argparse.Namespace) -> int:
    with open_db(args.state_dir) as db:
        rows = db.execute(
            "SELECT id, folder_path, created_at, status FROM organizer_runs ORDER BY id DESC LIMIT ?",
            (args.limit,),
        ).fetchall()
    if not rows:
        print("no runs recorded yet.")
        return 0
    for row in rows:
        print(f"[{row['id']}] folder={row['folder_path']} status={row['status']} created={row['created_at']}")
    return 0


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview, apply, and undo safe local file organization.",
    )
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Classify files and produce a preview report and plan.")
    scan.add_argument("--folder", required=True, help="Folder to scan, e.g. ~/Downloads.")
    scan.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    scan.add_argument("--include-low-confidence", action="store_true")
    scan.add_argument("--include-hidden", action="store_true")
    scan.set_defaults(func=command_scan)

    apply = subparsers.add_parser("apply", help="Apply a previously generated plan.")
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--confirm", required=True, help=f"Must be {CONFIRM_WORD}.")
    apply.set_defaults(func=command_apply)

    undo = subparsers.add_parser("undo", help="Reverse moves recorded in an action log.")
    undo.add_argument("--log", type=Path, required=True)
    undo.set_defaults(func=command_undo)

    runs = subparsers.add_parser("runs", help="List recent organizer runs.")
    runs.add_argument("--limit", type=int, default=10)
    runs.set_defaults(func=command_runs)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
