#!/usr/bin/env python3
"""Copy synthetic Lesson 2 fixtures to an owned runtime folder without overwriting."""
import argparse
import shutil
from pathlib import Path
from course_runtime import CourseError, REPO, cli_main, emit, write_json


SCENARIOS = {
    "knowledge-study-notes": "lesson-2-knowledge-study-notes",
    "knowledge-conflict-rules": "lesson-2-knowledge-conflict-rules",
    "knowledge-weekly-update": "lesson-2-knowledge-weekly-update",
    "organizer-student-files": "lesson-2-organizer-student-files",
    "organizer-freelancer-rules": "lesson-2-organizer-freelancer-rules",
    "organizer-safe-recovery": "lesson-2-organizer-safe-recovery",
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario", choices=SCENARIOS)
    p.add_argument("--output", type=Path)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    scenario = a.scenario or "lesson-2"
    fixture_name = SCENARIOS.get(a.scenario, "lesson-2")
    source = Path(__file__).resolve().parents[1] / "examples" / fixture_name
    output = a.output or REPO / ".local-state/course-demo" / fixture_name
    target = output.resolve()
    if not source.is_dir():
        raise CourseError("MISSING_FIXTURE", "The selected synthetic source fixture is unavailable.")
    if output.is_symlink() or target.exists():
        raise CourseError("WOULD_OVERWRITE", "Choose a fresh output folder; existing course work is preserved.")
    if not a.dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
        write_json(target / ".course-demo.json", {"synthetic": True, "lesson": 2, "scenario": scenario})
    emit({"status": "preview" if a.dry_run else "seeded", "output": str(target), "synthetic": True})


if __name__ == "__main__":
    cli_main(main)
