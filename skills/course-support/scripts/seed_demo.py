#!/usr/bin/env python3
"""Copy synthetic Lesson 2 fixtures to an owned runtime folder without overwriting."""
import argparse
import shutil
from pathlib import Path
from course_runtime import CourseError, REPO, cli_main, emit, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=REPO / ".local-state/course-demo/lesson-2")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    target = a.output.resolve()
    if a.output.is_symlink() or target.exists():
        raise CourseError("WOULD_OVERWRITE", "Choose a fresh output folder; existing course work is preserved.")
    if not a.dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(Path(__file__).resolve().parents[1] / "examples/lesson-2", target)
        write_json(target / ".course-demo.json", {"synthetic": True, "lesson": 2})
    emit({"status": "preview" if a.dry_run else "seeded", "output": str(target), "synthetic": True})


if __name__ == "__main__":
    cli_main(main)
