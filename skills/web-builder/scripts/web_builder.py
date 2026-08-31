#!/usr/bin/env python3
"""Inspect first, scaffold an empty static project, or record a reviewed existing-stack build."""
from __future__ import annotations
import argparse
import html
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        break
else:
    raise SystemExit("Install the course foundation (PR #222) before running this lesson.")
from course_runtime import Config, CourseError, Run, Store, add_storage_args, cli_main, digest, emit, file_hash, identifier, read_json, require_approval, write_json
from web_project import inspect, source_manifest

PACKAGE = Path(__file__).resolve().parents[1]


def validate_brief(brief: dict) -> dict:
    if not isinstance(brief, dict) or not all(isinstance(brief.get(k), str) and brief[k].strip() for k in ("purpose", "audience", "style_direction")):
        raise CourseError("INVALID_BRIEF", "Brief requires purpose, audience and style_direction strings.")
    if not isinstance(brief.get("constraints"), list) or not all(isinstance(x, str) for x in brief["constraints"]):
        raise CourseError("INVALID_BRIEF", "Brief requires a constraints string list.")
    sections = brief.get("sections")
    if not isinstance(sections, list) or not 1 <= len(sections) <= 8 or not all(isinstance(s, dict) and all(isinstance(s.get(k), str) and s[k].strip() for k in ("heading", "body")) for s in sections):
        raise CourseError("INVALID_BRIEF", "Provide 1–8 sections with heading and body.")
    return brief


def render(brief: dict) -> dict:
    validate_brief(brief)
    if brief["style_direction"] not in {"calm-editorial", "bold-contrast"}:
        raise CourseError("CUSTOM_BUILD_REQUIRED", "The starter supports calm-editorial or bold-contrast. For another style, have Codex build the requested design in context and use record.")
    supported = {"no_external_requests", "demo_form_only", "responsive", "keyboard_accessible"}
    if set(brief["constraints"]) - supported:
        raise CourseError("CUSTOM_BUILD_REQUIRED", "Unsupported constraints require a reviewed custom build; the starter must not silently ignore them.")
    sections = "\n".join(f'<section class="card" id="section-{i}"><span class="number">{i:02d}</span><h2>{html.escape(s["heading"])}</h2><p>{html.escape(s["body"])}</p></section>' for i, s in enumerate(brief["sections"], 1))
    values = {"{{purpose}}": html.escape(brief["purpose"]), "{{audience}}": html.escape(brief["audience"]), "{{sections}}": sections}
    output = {}
    for name in ("index.html", "style.css", "app.js"):
        text = (PACKAGE / "assets/site" / name).read_text(encoding="utf-8")
        for marker, value in values.items():
            text = text.replace(marker, value)
        output[name] = text
    if brief["style_direction"] == "bold-contrast":
        output["style.css"] += "\nbody{background:#111b2e;color:#f7f5ec} .card,form{background:#23334c;color:#fff} .contact{color:#193c3d} a{color:#d7ff61} input{background:#fff;color:#111} footer{color:#ddd}\n"
    return output


def build(store: Store, project: Path, project_id: str, brief: dict, confirm: str | None, update: bool = False) -> dict:
    identifier(project_id, "project id")
    project = project.resolve()
    context = inspect(project)
    rendered = render(brief)
    if context["exists"] and any(project.iterdir()):
        marker = project / ".course-project.json"
        if not update or not marker.is_file():
            raise CourseError("EXISTING_STACK", "Existing project preserved. Inspect its README and scripts, modify it with Codex, then use record; do not scaffold over it.")
        owned = read_json(marker)
        if owned.get("project_id") != project_id or any(not (project / name).is_file() or file_hash(project / name) != hashed for name, hashed in owned["generated_files"].items()):
            raise CourseError("LOCAL_EDITS", "Generated files were edited or belong to another project. Preserve them and use the existing-stack workflow.")
    preview = {"project_id": project_id, "context": context, "changed_files": sorted(rendered), "brief": brief, "ui_qa": "not_run"}
    if store.config.dry_run:
        return {"status": "preview", **preview}
    require_approval(confirm, "BUILD")
    node = shutil.which("node")
    if not node:
        raise CourseError("DEPENDENCY_MISSING", "Install a current Node.js LTS runtime to run the basic JavaScript syntax check.")
    run = Run(store, "web-builder", "Build from an approved course brief")
    run.save("running")
    with tempfile.TemporaryDirectory(prefix="course-web-build-") as staging:
        for name, content in rendered.items():
            Path(staging, name).write_text(content, encoding="utf-8")
        check = subprocess.run([node, "--check", str(Path(staging, "app.js"))], capture_output=True, timeout=30)
        if check.returncode:
            run.event("basic_build_failed", {"command": "node --check app.js", "exit_code": check.returncode})
            run.save("failed")
            raise CourseError("BUILD_FAILED", "The generated JavaScript failed syntax validation; existing project files were not changed.")
        project.mkdir(parents=True, exist_ok=True)
        for name in rendered:
            shutil.copyfile(Path(staging, name), project / name)
    files = source_manifest(project)
    write_json(project / ".course-project.json", {"project_id": project_id, "generated_files": {name: files[name] for name in rendered}})
    data = {"project_id": project_id, "brief": brief, "build_status": "succeeded", "check": {"command": "node --check app.js", "exit_code": 0},
            "changed_files": sorted(rendered), "source_files": files, "project_fingerprint": digest(files), "last_build_run_id": run.id, "ui_qa": "not_run"}
    old = store.maybe_get("web_projects", project_id)
    record = store.put("web_projects", project_id, data, expected_revision=old["revision"] if old else 0)
    run.artifact("web_build", "Basic build evidence", {"project_id": project_id, "revision": record["revision"], "project_fingerprint": data["project_fingerprint"], "changed_files": sorted(rendered), "ui_qa": "not_run"})
    run.save("succeeded")
    return {"status": "succeeded", "run_id": run.id, "project_id": project_id, "revision": record["revision"], "project": str(project), "changed_files": sorted(rendered), "project_fingerprint": data["project_fingerprint"], "ui_qa": "not_run"}


def record_build(store: Store, project: Path, project_id: str, command: list, confirm: str | None, brief: dict) -> dict:
    identifier(project_id, "project id")
    validate_brief(brief)
    context = inspect(project)
    if not context["exists"] or not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        raise CourseError("INVALID_INPUT", "Select an existing project and a reviewed JSON argv list for its build/type check.")
    if store.config.dry_run:
        return {"status": "preview", "context": context, "command": command, "brief": brief}
    require_approval(confirm, "BUILD_CHECK")
    run = Run(store, "web-builder", "Run the existing project's reviewed build check")
    run.save("running")
    try:
        result = subprocess.run(command, cwd=project, shell=False, capture_output=True, timeout=300)
        code = result.returncode
    except subprocess.TimeoutExpired:
        code = 124
    except OSError:
        code = 127
    state = "succeeded" if code == 0 else "failed"
    files = source_manifest(project)
    previous = store.maybe_get("web_projects", project_id)
    data = {"project_id": project_id, "brief": brief, "stack": context["stack"], "source_files": files, "project_fingerprint": digest(files), "build_status": state,
            "check": {"exit_code": code, "command_sha256": digest(command)}, "last_build_run_id": run.id, "ui_qa": "not_run"}
    rec = store.put("web_projects", project_id, data, expected_revision=previous["revision"] if previous else 0)
    run.artifact("web_build", "Existing-stack build evidence", {"project_id": project_id, "revision": rec["revision"], "exit_code": code, "project_fingerprint": digest(files)})
    run.save(state)
    return {"status": state, "run_id": run.id, "project_id": project_id, "revision": rec["revision"], "exit_code": code, "ui_qa": "not_run"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("inspect", "build", "record"):
        s = sub.add_parser(name)
        s.add_argument("--project", type=Path, required=True)
        if name != "inspect":
            s.add_argument("--project-id", default="course-site")
            s.add_argument("--confirm")
        if name == "build":
            s.add_argument("--brief", type=Path, required=True)
            s.add_argument("--update", action="store_true")
        if name == "record":
            s.add_argument("--command-file", type=Path, required=True)
            s.add_argument("--brief", type=Path, required=True)
    a = p.parse_args()
    if a.command == "inspect":
        emit(inspect(a.project))
        return
    store = Store(Config.from_args(a))
    if a.command == "build":
        result = build(store, a.project, a.project_id, read_json(a.brief), a.confirm, a.update)
    else:
        result = record_build(store, a.project, a.project_id, read_json(a.command_file), a.confirm, read_json(a.brief))
    emit(result)
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    cli_main(main)
