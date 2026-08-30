#!/usr/bin/env python3
"""Copy only course packages into repo-local Codex discovery; never use symlinks."""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from course_runtime import CourseError, REPO, cli_main, emit, read_json, write_json


def frontmatter(folder: Path) -> dict:
    text = (folder / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        raise CourseError("INVALID_SKILL", "Missing skill frontmatter: " + folder.name)
    values = {}
    for line in text.split("---", 2)[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip('\"\'')
    if values.get("name") != folder.name or not values.get("description"):
        raise CourseError("INVALID_SKILL", "Skill name/description does not match package: " + folder.name)
    return values


def tree_hash(folder: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if "__pycache__" in p.parts or p.suffix == ".pyc":
            continue
        if p.is_symlink():
            raise CourseError("UNSAFE_PATH", "Skill packages may not contain symlinks.")
        if p.is_file():
            h.update(p.relative_to(folder).as_posix().encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def packages(repo: Path, lesson: str) -> list[Path]:
    selected = []
    for path in sorted((repo / "skills").glob("*/course.json")):
        data = read_json(path)
        if lesson == "all" or str(data.get("lesson")) == lesson:
            frontmatter(path.parent)
            selected.append(path.parent)
    if not selected:
        raise CourseError("NOT_FOUND", "No course packages for this lesson in the current checkout.")
    return selected


def install(repo: Path, lesson: str, *, check: bool = False, dry_run: bool = False, replace: bool = False) -> dict:
    repo = repo.resolve()
    sources = packages(repo, lesson)
    agents = repo / ".agents"
    destination = agents / "skills"
    if agents.is_symlink() or destination.is_symlink():
        raise CourseError("UNSAFE_PATH", "Refusing a symlinked Codex installation directory.")
    manifest_path = agents / "course-installed.json"
    installed = read_json(manifest_path) if manifest_path.exists() else {}
    planned = []
    for source in sources:
        target = destination / source.name
        current_hash = tree_hash(source)
        if target.is_symlink():
            raise CourseError("UNSAFE_PATH", "Refusing a symlinked installed package.")
        if target.exists() and source.name not in installed:
            raise CourseError("UNMANAGED_SKILL", "Preserve the existing unowned skill: " + source.name)
        if target.exists() and tree_hash(target) != installed.get(source.name) and not replace:
            raise CourseError("LOCAL_EDITS", "Installed skill was edited. Copy changes to skills/ first, or explicitly use --replace: " + source.name)
        if check and (not target.exists() or tree_hash(target) != current_hash):
            raise CourseError("OUT_OF_SYNC", "Run setup to refresh: " + source.name)
        planned.append((source, target, current_hash))
    if not check and not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
        ignore = agents / ".gitignore"
        if not ignore.exists():
            ignore.write_text("*\n", encoding="utf-8")
        else:
            existing = ignore.read_text()
            additions = [x for x in ("skills/", "course-installed.json") if x not in existing.splitlines()]
            if additions:
                ignore.write_text(existing.rstrip() + "\n" + "\n".join(additions) + "\n")
        for source, target, current_hash in planned:
            # Validate before replacing any owned package; stage a complete copy first.
            with tempfile.TemporaryDirectory(prefix="course-install-", dir=agents) as staging:
                staged = Path(staging) / source.name
                shutil.copytree(source, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                if target.exists():
                    shutil.rmtree(target)
                staged.replace(target)
            installed[source.name] = current_hash
            write_json(manifest_path, installed)
    return {"status": "checked" if check else "preview" if dry_run else "installed", "skills": [p.name for p in sources],
            "discovery": ".agents/skills", "source_of_truth": "skills", "next": "Invoke $skill-name in Codex; reload/restart if the list is stale."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lesson", choices=("2", "3", "4", "5", "all"), default="all")
    p.add_argument("--repo", type=Path, default=REPO)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--check", action="store_true")
    p.add_argument("--replace", action="store_true", help="Replace edited generated copies; never changes canonical skills/.")
    a = p.parse_args()
    emit(install(a.repo, a.lesson, check=a.check, dry_run=a.dry_run, replace=a.replace))


if __name__ == "__main__":
    cli_main(main)
