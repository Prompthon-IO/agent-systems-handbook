#!/usr/bin/env python3
"""Preview-first local cleanup helper for the garbage-collector skill."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RULES = SKILL_DIR / "references" / "cleanup-rules.csv"
DEFAULT_STATE = Path(
    os.environ.get(
        "GARBAGE_COLLECTOR_STATE",
        str(Path.home() / ".codex" / "state" / "garbage-collector"),
    )
)
TRASH_DIR = Path.home() / ".Trash"
DOWNLOADS_DIR = Path.home() / "Downloads"
CONFIRM_WORD = "CLEANUP"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def expand_path(raw: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def readable_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def load_rules(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        row
        for row in rows
        if row.get("enabled", "").strip().lower() in {"true", "yes", "1", "on"}
    ]


def ensure_state_dirs(state_dir: Path) -> dict[str, Path]:
    paths = {
        "reports": state_dir / "reports",
        "plans": state_dir / "plans",
        "logs": state_dir / "logs",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def is_safe_target(path: Path) -> bool:
    blocked = {
        Path("/"),
        Path("/System"),
        Path("/Library"),
        Path("/Applications"),
        Path("/bin"),
        Path("/sbin"),
        Path("/usr"),
        Path("/var"),
        Path("/etc"),
        Path("/private"),
    }
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        return False
    return resolved not in blocked


def target_in_scope(rule_path: Path, targets: list[Path]) -> bool:
    for target in targets:
        try:
            if target.resolve() == rule_path.resolve():
                return True
        except FileNotFoundError:
            continue
    return False


def file_age_days(path: Path) -> float:
    return max(0.0, (datetime.now().timestamp() - path.stat().st_mtime) / 86400)


def path_size(path: Path) -> int:
    if path.is_symlink():
        return path.lstat().st_size
    if path.is_file():
        return path.stat().st_size
    total = 0
    if path.is_dir():
        for child in path.rglob("*"):
            try:
                if child.is_symlink():
                    total += child.lstat().st_size
                elif child.is_file():
                    total += child.stat().st_size
            except (FileNotFoundError, PermissionError, OSError):
                continue
    return total


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_trash_candidates(rule: dict[str, str], targets: list[Path]) -> list[dict[str, Any]]:
    trash_path = expand_path(rule.get("default_path") or str(TRASH_DIR))
    if not trash_path.exists() or not target_in_scope(trash_path, targets):
        return []

    min_age = float(rule.get("min_age_days") or 0)
    suggestions: list[dict[str, Any]] = []
    for child in sorted(trash_path.iterdir(), key=lambda p: p.name.lower()):
        try:
            age = file_age_days(child)
            if age < min_age:
                continue
            size = path_size(child)
        except (FileNotFoundError, PermissionError, OSError):
            continue
        suggestions.append(
            {
                "id": f"trash-{len(suggestions) + 1}",
                "rule_id": rule["rule_id"],
                "rule_name": rule["name"],
                "action": rule["default_action"],
                "path": str(child),
                "size_bytes": size,
                "confidence": "high",
                "reason": f"Already in Trash and older than {min_age:g} days.",
                "destructive": True,
            }
        )
    return suggestions


def find_duplicate_downloads(rule: dict[str, str], targets: list[Path]) -> list[dict[str, Any]]:
    downloads_path = expand_path(rule.get("default_path") or str(DOWNLOADS_DIR))
    if not downloads_path.exists() or not target_in_scope(downloads_path, targets):
        return []

    by_size: dict[int, list[Path]] = {}
    for path in downloads_path.rglob("*"):
        try:
            if path.is_symlink() or not path.is_file():
                continue
            by_size.setdefault(path.stat().st_size, []).append(path)
        except (FileNotFoundError, PermissionError, OSError):
            continue

    suggestions: list[dict[str, Any]] = []
    for size, paths in sorted(by_size.items()):
        if size == 0 or len(paths) < 2:
            continue
        by_hash: dict[str, list[Path]] = {}
        for path in paths:
            try:
                by_hash.setdefault(sha256_file(path), []).append(path)
            except (FileNotFoundError, PermissionError, OSError):
                continue
        for digest, duplicates in by_hash.items():
            if len(duplicates) < 2:
                continue
            keep = sorted(duplicates, key=lambda p: (-p.stat().st_mtime, str(p)))[0]
            for duplicate in sorted(p for p in duplicates if p != keep):
                suggestions.append(
                    {
                        "id": f"duplicate-{len(suggestions) + 1}",
                        "rule_id": rule["rule_id"],
                        "rule_name": rule["name"],
                        "action": rule["default_action"],
                        "path": str(duplicate),
                        "keep_path": str(keep),
                        "size_bytes": size,
                        "confidence": "high",
                        "reason": f"Same size and SHA-256 hash as {keep}.",
                        "hash": digest,
                        "destructive": False,
                    }
                )
    return suggestions


def build_plan(
    rules: list[dict[str, str]], rules_file: Path, targets: list[Path], state_dir: Path
) -> dict[str, Any]:
    suggestions: list[dict[str, Any]] = []
    for rule in rules:
        if rule.get("rule_id") == "trash-can":
            suggestions.extend(find_trash_candidates(rule, targets))
        elif rule.get("rule_id") == "duplicate-downloads":
            suggestions.extend(find_duplicate_downloads(rule, targets))

    rid = run_id()
    return {
        "run_id": rid,
        "created_at": utc_now(),
        "targets": [str(path) for path in targets],
        "rules_file": str(rules_file),
        "suggestions": suggestions,
        "state_dir": str(state_dir),
    }


def write_report(plan: dict[str, Any], report_path: Path) -> None:
    suggestions = plan["suggestions"]
    total_size = sum(int(item.get("size_bytes", 0)) for item in suggestions)
    destructive = sum(1 for item in suggestions if item.get("destructive"))

    lines = [
        "# Garbage Collector Preview",
        "",
        f"- Run: `{plan['run_id']}`",
        f"- Created: `{plan['created_at']}`",
        f"- Targets: {', '.join(f'`{target}`' for target in plan['targets'])}",
        f"- Suggestions: {len(suggestions)}",
        f"- Estimated reclaimable size: {readable_size(total_size)}",
        f"- Permanent-delete suggestions: {destructive}",
        "",
        "## Suggestions",
        "",
    ]
    if suggestions:
        lines.append("| Rule | Action | Size | Path | Reason |")
        lines.append("| --- | --- | ---: | --- | --- |")
        for item in suggestions:
            path = str(item["path"]).replace("|", "\\|")
            reason = str(item.get("reason", "")).replace("|", "\\|")
            lines.append(
                f"| {item['rule_id']} | {item['action']} | "
                f"{readable_size(int(item.get('size_bytes', 0)))} | `{path}` | {reason} |"
            )
    else:
        lines.append("No cleanup suggestions found for the selected rules and targets.")

    lines.extend(
        [
            "",
            "## Approval",
            "",
            "Run `apply --confirm CLEANUP --plan <plan.json>` only after user approval.",
            "Add `--allow-permanent-delete` only when the user explicitly approves permanent Trash deletion.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def command_scan(args: argparse.Namespace) -> int:
    rules = load_rules(args.rules)
    targets = [expand_path(value) for value in (args.target or [str(DOWNLOADS_DIR), str(TRASH_DIR)])]
    unsafe = [path for path in targets if not is_safe_target(path)]
    if unsafe:
        print("Refusing unsafe scan target(s):", ", ".join(str(path) for path in unsafe), file=sys.stderr)
        return 2

    paths = ensure_state_dirs(args.state_dir)
    plan = build_plan(rules, args.rules, targets, args.state_dir)
    plan_path = paths["plans"] / f"{plan['run_id']}-plan.json"
    report_path = paths["reports"] / f"{plan['run_id']}-preview.md"
    plan["plan_path"] = str(plan_path)
    plan["report_path"] = str(report_path)

    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    write_report(plan, report_path)

    total_size = sum(int(item.get("size_bytes", 0)) for item in plan["suggestions"])
    print(f"report={report_path}")
    print(f"plan={plan_path}")
    print(f"suggestions={len(plan['suggestions'])}")
    print(f"estimated_reclaimable={readable_size(total_size)}")
    return 0


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def safe_move_to_quarantine(source: Path, quarantine_root: Path) -> Path:
    relative_name = source.name
    destination = unique_destination(quarantine_root / relative_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    return destination


def permanently_delete(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def command_apply(args: argparse.Namespace) -> int:
    if args.confirm != CONFIRM_WORD:
        print(f"Refusing to apply without --confirm {CONFIRM_WORD}", file=sys.stderr)
        return 2

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    paths = ensure_state_dirs(args.state_dir)
    log_path = paths["logs"] / f"{plan['run_id']}-actions.json"
    quarantine_root = TRASH_DIR / f"garbage-collector-quarantine-{plan['run_id']}"
    actions: list[dict[str, Any]] = []

    for suggestion in plan.get("suggestions", []):
        source = Path(suggestion["path"])
        record = {
            "suggestion_id": suggestion["id"],
            "rule_id": suggestion["rule_id"],
            "action": suggestion["action"],
            "old_path": str(source),
            "status": "pending",
            "logged_at": utc_now(),
        }
        try:
            if not source.exists():
                record["status"] = "skipped"
                record["reason"] = "source path no longer exists"
            elif suggestion["action"] == "move_to_trash_quarantine":
                destination = safe_move_to_quarantine(source, quarantine_root)
                record["status"] = "moved"
                record["new_path"] = str(destination)
            elif suggestion["action"] == "permanent_delete":
                if not args.allow_permanent_delete:
                    record["status"] = "skipped"
                    record["reason"] = "permanent deletion requires --allow-permanent-delete"
                else:
                    source.resolve().relative_to(TRASH_DIR.resolve())
                    permanently_delete(source)
                    record["status"] = "deleted"
                    record["undoable"] = False
            else:
                record["status"] = "skipped"
                record["reason"] = f"unsupported action: {suggestion['action']}"
        except Exception as exc:  # noqa: BLE001 - log and continue cleanup actions.
            record["status"] = "failed"
            record["reason"] = str(exc)
        actions.append(record)

    log = {"run_id": plan["run_id"], "created_at": utc_now(), "actions": actions}
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"log={log_path}")
    print(f"moved={sum(1 for item in actions if item['status'] == 'moved')}")
    print(f"deleted={sum(1 for item in actions if item['status'] == 'deleted')}")
    print(f"skipped={sum(1 for item in actions if item['status'] == 'skipped')}")
    print(f"failed={sum(1 for item in actions if item['status'] == 'failed')}")
    return 0


def command_undo(args: argparse.Namespace) -> int:
    log = json.loads(args.log.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    for action in log.get("actions", []):
        if action.get("status") != "moved" or not action.get("new_path"):
            continue
        source = Path(action["new_path"])
        destination = Path(action["old_path"])
        record = {"old_path": str(destination), "new_path": str(source), "status": "pending"}
        try:
            if not source.exists():
                record["status"] = "skipped"
                record["reason"] = "quarantined path no longer exists"
            elif destination.exists():
                record["status"] = "skipped"
                record["reason"] = "original path already exists"
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(destination))
                record["status"] = "restored"
        except Exception as exc:  # noqa: BLE001 - keep undo best-effort.
            record["status"] = "failed"
            record["reason"] = str(exc)
        results.append(record)

    print(f"restored={sum(1 for item in results if item['status'] == 'restored')}")
    print(f"skipped={sum(1 for item in results if item['status'] == 'skipped')}")
    print(f"failed={sum(1 for item in results if item['status'] == 'failed')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview and apply local cleanup suggestions.")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Create a cleanup preview and plan.")
    scan.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    scan.add_argument("--target", action="append", help="Path to scan. Can be repeated.")
    scan.set_defaults(func=command_scan)

    apply = subparsers.add_parser("apply", help="Apply a previously generated cleanup plan.")
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--confirm", required=True)
    apply.add_argument("--allow-permanent-delete", action="store_true")
    apply.set_defaults(func=command_apply)

    undo = subparsers.add_parser("undo", help="Undo reversible move actions from a log.")
    undo.add_argument("--log", type=Path, required=True)
    undo.set_defaults(func=command_undo)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
