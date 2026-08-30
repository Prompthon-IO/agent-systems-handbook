#!/usr/bin/env python3
"""Run a reviewed, ordered manifest without a shell, scheduler or automatic retry."""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        break
from course_runtime import Config, CourseError, REPO, Run, Store, add_storage_args, cli_main, digest, emit, identifier, read_json, require_approval, write_json


def validate(definition: dict) -> dict:
    if not isinstance(definition, dict):
        raise CourseError("INVALID_WORKFLOW", "Workflow must be a JSON object.")
    identifier(definition.get("id"), "workflow id")
    if definition.get("trigger") != {"type": "manual"}:
        raise CourseError("INVALID_WORKFLOW", "Version 1 supports manual triggers only.")
    steps = definition.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 20:
        raise CourseError("INVALID_WORKFLOW", "Provide 1–20 ordered steps.")
    ids = set()
    for step in steps:
        sid = identifier(step.get("id"), "step id")
        argv = step.get("argv")
        if sid in ids or not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x and "\x00" not in x for x in argv):
            raise CourseError("INVALID_WORKFLOW", "Use unique step ids and an argv string array; no shell command strings.")
        if not isinstance(step.get("approval_required"), bool) or not isinstance(step.get("retryable"), bool):
            raise CourseError("INVALID_WORKFLOW", "Each step explicitly declares approval_required and retryable.")
        if not isinstance(step.get("timeout_seconds", 60), int) or not 1 <= step.get("timeout_seconds", 60) <= 300:
            raise CourseError("INVALID_WORKFLOW", "Step timeout must be 1–300 seconds.")
        ids.add(sid)
    return definition


def expand(argv: list, store: Store) -> list:
    replacements = {"{repo}": str(REPO), "{python}": sys.executable, "{workspace_dir}": str(store.root),
                    "{state_dir}": str(store.config.state_dir), "{organization}": store.scope[0], "{workspace}": store.scope[1]}
    output = []
    for arg in argv:
        for key, value in replacements.items():
            arg = arg.replace(key, value)
        output.append(arg)
    return output


def execute(store: Store, definition: dict, confirm: str | None, approved_steps: list, *, previous_id: str | None = None) -> dict:
    validate(definition)
    fingerprint = digest(definition)
    if store.config.dry_run:
        return {"status": "preview", "workflow_sha256": fingerprint, "steps": definition["steps"]}
    require_approval(confirm, fingerprint)
    unknown = set(approved_steps) - {s["id"] for s in definition["steps"]}
    if unknown:
        raise CourseError("INVALID_INPUT", "Approval names a step outside this workflow.")
    journal = None
    if previous_id:
        identifier(previous_id, "prior run")
        prior_path = store.root / "workflow-journals" / (previous_id + ".json")
        if not prior_path.is_file():
            raise CourseError("RECOVERY_REQUIRED", "Retry requires the local journal; do not infer executed steps from an incomplete remote record.")
        journal = read_json(prior_path)
        if journal["workflow_sha256"] != fingerprint or journal["scope"] != list(store.scope):
            raise CourseError("WORKFLOW_CHANGED", "The workflow or workspace changed; review a new run instead of retrying.")
        if any(s["status"] == "running" for s in journal["steps"]):
            raise CourseError("UNCERTAIN_STEP", "A step was interrupted while running. Inspect its effects; automatic retry would risk duplication.")
        for step, state in zip(definition["steps"], journal["steps"]):
            if state["status"] == "failed" and (not step["retryable"] or state.get("retryable") is False):
                raise CourseError("NOT_RETRYABLE", "A failed step is not declared retryable; review its effects before a new run.")
    run = Run(store, "personal-workflow-automation", "Run a reviewed manual workflow")
    states = journal["steps"] if journal else [{"id": s["id"], "status": "pending"} for s in definition["steps"]]
    journal = {"run_id": run.id, "scope": list(store.scope), "workflow_id": definition["id"], "workflow_sha256": fingerprint, "steps": states, "retry_of": previous_id}
    log = store.root / "workflow-journals" / (run.id + ".json")
    run.data["metadata"] = {"workflow_id": definition["id"], "workflow_sha256": fingerprint, "retry_of": previous_id}
    run.save("running")
    write_json(log, journal)
    # Child steps get no course bearer token or production database credentials by default.
    child_env = {k: v for k, v in os.environ.items() if not any(word in k.upper() for word in ("TOKEN", "SECRET", "PASSWORD", "DATABASE_URL", "API_KEY"))}
    child_env["PROMPTHON_STORAGE"] = "local"
    for step, state in zip(definition["steps"], states):
        if state["status"] == "succeeded":
            run.event("step_reused", {"step_id": step["id"], "previous_run_id": previous_id})
            continue
        if step["approval_required"] and step["id"] not in approved_steps:
            state["status"] = "awaiting_approval"
            write_json(log, journal)
            run.artifact("workflow_steps", "Approval gate reached", states)
            run.save("awaiting_approval")
            return {"status": "awaiting_approval", "run_id": run.id, "step_id": step["id"], "journal": str(log), "workflow_sha256": fingerprint}
        state["status"] = "running"
        write_json(log, journal)
        run.event("step_started", {"step_id": step["id"]})
        run.save("running")
        try:
            result = subprocess.run(expand(step["argv"], store), cwd=REPO, env=child_env, shell=False,
                                    capture_output=True, timeout=step.get("timeout_seconds", 60))
            state.update(status="succeeded" if result.returncode == 0 else "failed", returncode=result.returncode,
                         stdout_sha256=digest(result.stdout.decode(errors="replace")), stderr_sha256=digest(result.stderr.decode(errors="replace")))
        except subprocess.TimeoutExpired:
            state.update(status="failed", error="timeout_effects_require_review", retryable=False)
            # A timeout may have mutated files. Never automatically retry it.
        except OSError:
            state.update(status="failed", error="command_unavailable")
        write_json(log, journal)
        run.event("step_finished", dict(state))
        if state["status"] == "failed":
            run.artifact("workflow_steps", "Failed workflow step", states)
            run.save("failed")
            return {"status": "failed", "run_id": run.id, "failed_step": step["id"], "retryable": step["retryable"] and state.get("retryable", True), "journal": str(log)}
        run.save("running")  # Stop before the next step if remote acknowledgement/readback fails.
    run.artifact("workflow_steps", "Completed ordered steps", states)
    run.save("succeeded")
    return {"status": "succeeded", "run_id": run.id, "workflow_id": definition["id"], "steps": states, "journal": str(log)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    sub = p.add_subparsers(dest="command", required=True)
    define = sub.add_parser("define")
    define.add_argument("--file", type=Path, required=True)
    define.add_argument("--expected-revision", type=int, default=0)
    for command in ("preview", "run", "retry"):
        c = sub.add_parser(command)
        c.add_argument("--workflow", required=True)
        if command != "preview":
            c.add_argument("--confirm")
            c.add_argument("--approve-step", action="append", default=[])
        if command == "retry":
            c.add_argument("--run-id", required=True)
    a = p.parse_args()
    store = Store(Config.from_args(a))
    if a.command == "define":
        definition = validate(read_json(a.file))
        record = store.put("workflow_definitions", definition["id"], definition, expected_revision=a.expected_revision)
        emit({"workflow_id": definition["id"], "workflow_sha256": digest(definition), "revision": record["revision"], "status": "preview" if a.dry_run else "defined"})
        return
    definition = validate(store.get("workflow_definitions", a.workflow)["data"])
    if a.command == "preview":
        emit({"workflow_sha256": digest(definition), "definition": definition, "approval_steps": [s["id"] for s in definition["steps"] if s["approval_required"]]})
    else:
        result = execute(store, definition, a.confirm, a.approve_step, previous_id=getattr(a, "run_id", None))
        emit(result)
        return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    cli_main(main)
