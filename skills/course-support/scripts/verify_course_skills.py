#!/usr/bin/env python3
"""Check installed-branch course contracts, then run all course behavior tests."""
import json
import subprocess
import sys
from pathlib import Path

from course_runtime import REPO
from setup_course_skills import frontmatter


def main():
    required = ["README.md", "SKILL.md", "agents/openai.yaml", "references/source-notes.md", "references/safety-rules.md", "references/persistence-contract.md"]
    lessons = {}
    tests = [REPO / "skills/course-support/tests"]
    for path in sorted((REPO / "skills").glob("*/course.json")):
        package = path.parent
        spec = json.loads(path.read_text())
        frontmatter(package)
        for name in required:
            assert (package / name).is_file(), f"Missing {package.name}/{name}"
        assert list((package / "examples").glob("*")), f"Missing fixture for {package.name}"
        assert f"${package.name}" in (package / "agents/openai.yaml").read_text()
        assert spec["capability"] not in lessons.setdefault(spec["lesson"], set()), "Overlapping capability"
        lessons[spec["lesson"]].add(spec["capability"])
        assert (package / spec["entrypoint"]).is_file()
        test_folder = package / "tests"
        # Some packages expose only a Node harness, exercised by a Python
        # lifecycle test elsewhere. Python 3.14 rejects empty discovery runs.
        if any(test_folder.rglob("test_*.py")):
            tests.append(test_folder)
    assert lessons, "No course packages found"
    for lesson, capabilities in lessons.items():
        assert len(capabilities) == 3, f"Lesson {lesson} must have three distinct capabilities"
    for folder in tests:
        subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(folder), "-p", "test_*.py", "-v"], cwd=REPO, check=True)
    print("Course packages and behavior verified:", sum(map(len, lessons.values())), "skills", sorted(lessons))


if __name__ == "__main__":
    main()
