"""Small shared web-project inspection helper; source bytes never enter persistence."""
import os
from pathlib import Path

from course_runtime import CourseError, digest, file_hash, read_json

IGNORED = {".git", "node_modules", ".next", "dist", "build", ".venv", "__pycache__", ".local-state", ".agents", ".vercel"}


def source_manifest(project: Path) -> dict:
    project = project.resolve()
    if not project.is_dir():
        raise CourseError("INVALID_PROJECT", "Project must be an existing directory.")
    files = {}
    for current, dirs, names in os.walk(project, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED and not Path(current, d).is_symlink())
        for name in sorted(names):
            path = Path(current, name)
            if name.startswith(".env") or name == ".course-project.json" or path.is_symlink():
                continue
            if len(files) >= 500:
                raise CourseError("PROJECT_TOO_LARGE", "The classroom manifest supports up to 500 source files; select a smaller project root.")
            files[path.relative_to(project).as_posix()] = file_hash(path)
    return files


def inspect(project: Path) -> dict:
    if not project.exists():
        return {"exists": False, "stack": "empty", "scripts": {}, "source_files": {}}
    package = read_json(project / "package.json") if (project / "package.json").is_file() else {}
    deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    stack = "next" if "next" in deps else "react" if "react" in deps else "node" if package else "static_or_other"
    files = source_manifest(project)
    return {"exists": True, "stack": stack, "scripts": package.get("scripts", {}), "source_files": files,
            "project_fingerprint": digest(files), "readme_present": (project / "README.md").exists(),
            "course_owned": (project / ".course-project.json").is_file()}
