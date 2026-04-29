#!/usr/bin/env python3
"""Fail when tracked paths have case-only conflicts or casing drift."""

from __future__ import annotations

import subprocess
import sys
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def git_tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def find_case_conflicts(paths: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        grouped[path.lower()].append(path)
    return {
        normalized: variants
        for normalized, variants in grouped.items()
        if len(variants) > 1
    }


def actual_case_path(repo_root: Path, relative_path: str) -> str | None:
    current_dir = repo_root
    actual_parts: list[str] = []

    for part in Path(relative_path).parts:
        try:
            entries = {entry.name.lower(): entry.name for entry in current_dir.iterdir()}
        except FileNotFoundError:
            return None

        actual_name = entries.get(part.lower())
        if actual_name is None:
            return None

        actual_parts.append(actual_name)
        current_dir = current_dir / actual_name

    return "/".join(actual_parts)


def find_case_mismatches(paths: list[str]) -> list[tuple[str, str]]:
    mismatches: list[tuple[str, str]] = []
    for path in paths:
        actual_path = actual_case_path(REPO_ROOT, path)
        if actual_path is None:
            continue
        if actual_path != path:
            mismatches.append((path, actual_path))
    return mismatches


def main() -> int:
    try:
        paths = git_tracked_paths()
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr)
        return exc.returncode

    conflicts = find_case_conflicts(paths)
    mismatches = find_case_mismatches(paths)

    if not conflicts and not mismatches:
        print("Filename casing check passed.")
        return 0

    if conflicts:
        print("Case-only path conflicts detected among tracked files:")
        for variants in conflicts.values():
            print(f"  - {' | '.join(sorted(variants))}")

    if mismatches:
        print("Tracked paths whose casing does not match the working tree:")
        for tracked_path, actual_path in mismatches:
            print(f"  - git: {tracked_path}")
            print(f"    fs:  {actual_path}")

    print()
    print("Fix the casing before push, for example with:")
    print("  git mv path/to/File.tmp path/to/file.tmp")
    print("  git mv path/to/file.tmp path/to/file.md")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
