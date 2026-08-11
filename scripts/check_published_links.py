#!/usr/bin/env python3
"""Reject internal MDX links that publish as `.mdx` site routes."""

from __future__ import annotations

import posixpath
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


REPO_ROOT = Path(__file__).resolve().parent.parent
FENCE_RE = re.compile(r"^\s{0,3}(?P<marker>`{3,}|~{3,})")
INTERNAL_MDX_LINK_RE = re.compile(
    r"(?<!!)\[[^\]\n]+\]\("
    r"(?P<target>(?:/|\./|\.\./)[^)\s]+?\.mdx(?:[?#][^)\s]*)?)"
    r"(?:\s+[\"'][^)\n]*[\"'])?\)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Violation:
    path: Path
    line_number: int
    target: str
    suggested_route: str


def discover_mdx_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(
        REPO_ROOT / relative_path
        for relative_path in result.stdout.splitlines()
        if relative_path.lower().endswith(".mdx")
    )


def extensionless_route(source_path: Path, target: str) -> str:
    parsed = urlsplit(target)
    target_path = parsed.path

    if target_path.startswith("/"):
        repo_path = PurePosixPath(target_path.lstrip("/"))
    else:
        source_parent = PurePosixPath(source_path.relative_to(REPO_ROOT).parent.as_posix())
        repo_path = PurePosixPath(posixpath.normpath((source_parent / target_path).as_posix()))

    route_path = repo_path.as_posix()[: -len(".mdx")]
    if route_path == "index":
        route_path = ""
    elif route_path.endswith("/index"):
        route_path = route_path[: -len("/index")]

    route = f"/{route_path}" if route_path else "/"
    if parsed.query:
        route += f"?{parsed.query}"
    if parsed.fragment:
        route += f"#{parsed.fragment}"
    return route


def find_violations(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    fence: tuple[str, int] | None = None

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group("marker")
            if fence is None:
                fence = (marker[0], len(marker))
            elif marker[0] == fence[0] and len(marker) >= fence[1]:
                fence = None
            continue

        if fence is not None:
            continue

        for match in INTERNAL_MDX_LINK_RE.finditer(line):
            target = match.group("target")
            violations.append(
                Violation(
                    path=path,
                    line_number=line_number,
                    target=target,
                    suggested_route=extensionless_route(path, target),
                )
            )

    return violations


def main() -> int:
    try:
        violations = [
            violation
            for path in discover_mdx_files()
            for violation in find_violations(path)
        ]
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Unable to check published links: {exc}", file=sys.stderr)
        return 2

    if not violations:
        print("Published internal link check passed.")
        return 0

    print("Internal MDX links must use extensionless published routes:")
    for violation in violations:
        relative_path = violation.path.relative_to(REPO_ROOT)
        print(
            f"  - {relative_path}:{violation.line_number}: "
            f"{violation.target} -> {violation.suggested_route}"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
