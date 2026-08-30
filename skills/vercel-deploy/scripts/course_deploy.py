#!/usr/bin/env python3
"""Preview-first Vercel deployment with source/test gates and provider plus URL readback."""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        sys.path.insert(0, str(parent / "skills/web-builder/scripts"))
        break
else:
    raise SystemExit("Install the course foundation (PR #222) before running this lesson.")
from course_runtime import Config, CourseError, NoRedirect, Run, Store, add_storage_args, cli_main, digest, emit, identifier, read_json, require_approval, write_json
from web_project import source_manifest


def deployment_host(value: str) -> str:
    parsed = urllib.parse.urlsplit(value if "://" in value else "https://" + value)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port or parsed.path not in {"", "/"} or parsed.query or parsed.fragment or not re.fullmatch(r"[a-zA-Z0-9-]+\.vercel\.app", parsed.hostname or ""):
        raise CourseError("UNSAFE_URL", "Use the exact HTTPS *.vercel.app deployment origin from Vercel; no custom redirect, credentials, path or query.")
    return parsed.hostname


class Provider:
    def __init__(self, token_file: Path | None = None, team_id: str | None = None):
        self.token_file, self.team_id = token_file, team_id
        self.opener = urllib.request.build_opener(NoRedirect())

    def deployment(self, deployment_id: str) -> dict:
        if deployment_id.startswith("dpl_"):
            identifier(deployment_id, "deployment id")
            key = deployment_id
        else:
            key = deployment_host(deployment_id)
        token = self.token_file.read_text().strip() if self.token_file else os.getenv("VERCEL_ACCESS_TOKEN", "")
        if not token or any(c.isspace() for c in token):
            raise CourseError("PROVIDER_AUTH_REQUIRED", "Configure VERCEL_ACCESS_TOKEN or a private --vercel-token-file. Never put it in a brief or command argument.")
        query = {"withGitRepoInfo": "true"}
        if self.team_id:
            query["teamId"] = identifier(self.team_id, "team id")
        request = urllib.request.Request("https://api.vercel.com/v13/deployments/" + urllib.parse.quote(key, safe="") + "?" + urllib.parse.urlencode(query), headers={"Authorization": "Bearer " + token})
        try:
            with self.opener.open(request, timeout=20) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise CourseError("PROVIDER_RESPONSE_TOO_LARGE", "Provider response exceeds the bounded verifier limit.")
                data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            raise CourseError("PROVIDER_HTTP_ERROR", f"Provider returned HTTP {status}; raw response and credentials were not saved.") from None
        except (urllib.error.URLError, TimeoutError, ValueError):
            raise CourseError("PROVIDER_UNAVAILABLE", "Provider readback failed; do not redeploy to recover an unknown result.", retryable=True) from None
        # The full owner response may contain environment variables. Retain only this allowlist.
        git_source, meta = data.get("gitSource") or {}, data.get("meta") or {}
        return {"deployment_id": data.get("id"), "url": data.get("url"), "project_id": data.get("projectId"),
                "target": data.get("target"), "ready_state": data.get("readyState"),
                "commit_sha": git_source.get("sha") or meta.get("githubCommitSha") or meta.get("gitlabCommitSha") or meta.get("gitCommitSha")}

    def url_readback(self, host: str, expected_text: str) -> dict:
        # Never send the API credential to a deployment. Protected previews remain unverified.
        host = deployment_host(host)
        try:
            with self.opener.open("https://" + host, timeout=20) as response:
                body = response.read(1_000_001)
                matched = len(body) <= 1_000_000 and expected_text in body.decode("utf-8", errors="replace")
                return {"http_status": response.status, "expected_text_found": matched, "status": "passed" if response.status == 200 and matched else "failed"}
        except (urllib.error.URLError, TimeoutError) as exc:
            if isinstance(exc, urllib.error.HTTPError):
                exc.close()
            return {"status": "unverified", "reason": "URL inaccessible, redirected or protected; inspect it with the authorized browser."}


def git_commit(project: Path) -> str:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project, capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", "."], cwd=project, capture_output=True, text=True, check=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        raise CourseError("COMMIT_REQUIRED", "Commit the reviewed project in its intended repository before deployment.") from None
    if status or not re.fullmatch(r"[0-9a-f]{40,64}", commit):
        raise CourseError("DIRTY_PROJECT", "Commit the reviewed project, then rerun browser tests before deploying. Uncommitted files cannot be attributed to a deployment commit.")
    return commit


def gate(store: Store, project: Path, project_id: str, test_id: str, expected_commit: str) -> dict:
    fingerprint = digest(source_manifest(project))
    build = store.get("web_projects", project_id)["data"]
    test = store.get("web_test_runs", test_id)["data"]
    if build.get("build_status") != "succeeded" or build.get("project_fingerprint") != fingerprint or test.get("status") != "passed" or test.get("project_id") != project_id or test.get("project_fingerprint") != fingerprint:
        raise CourseError("QA_REQUIRED", "Build and passing browser evidence must match the current project sources and project id.")
    commit = git_commit(project)
    if commit != expected_commit:
        raise CourseError("COMMIT_MISMATCH", "The expected deployment commit is not the current committed project.")
    return {"project_id": project_id, "project_fingerprint": fingerprint, "test_id": test_id, "commit_sha": commit}


def verify(store: Store, provider: Provider, evidence: dict, deployment_id: str, vercel_project: str, target: str, expected_text: str) -> dict:
    if store.config.dry_run:
        return {"status": "preview", "target": target, "deployment_id": deployment_id, **evidence}
    run = Run(store, "vercel-deploy", "Verify provider deployment identity and actual page")
    run.save("running")
    try:
        remote = provider.deployment(deployment_id)
        if not remote.get("deployment_id") or remote["project_id"] != vercel_project:
            raise CourseError("DEPLOYMENT_MISMATCH", "Provider deployment does not belong to the selected Vercel project.")
        actual_target = "preview" if remote["target"] in {None, "preview"} else remote["target"]
        if actual_target != target or remote["commit_sha"] != evidence["commit_sha"]:
            raise CourseError("DEPLOYMENT_MISMATCH", "Provider target or commit differs, or commit attribution is missing. Do not claim deployment verified.")
        host = deployment_host(remote["url"])
        readback = provider.url_readback(host, expected_text) if remote["ready_state"] == "READY" else {"status": "not_run"}
        status = "verified" if readback["status"] == "passed" else "failed" if remote["ready_state"] in {"ERROR", "CANCELED"} else "unverified"
        data = {**evidence, **remote, "url": "https://" + host, "target": actual_target, "status": status,
                "url_readback": readback, "expected_text_sha256": digest(expected_text)}
        old = store.maybe_get("deployment_records", remote["deployment_id"])
        rec = store.put("deployment_records", remote["deployment_id"], data, expected_revision=old["revision"] if old else 0)
        run.artifact("deployment", "Provider and URL readback", {"deployment_id": remote["deployment_id"], "revision": rec["revision"], "status": status})
        run.save("succeeded" if status == "verified" else "failed" if status == "failed" else "partial")
        return {"run_id": run.id, **data}
    except CourseError as exc:
        run.event("verification_failed", {"error": exc.code})
        run.save("failed")
        raise


def deploy(store: Store, provider: Provider, project: Path, evidence: dict, target: str, baseline_id: str, attempt: str, confirm: str | None, production_approved: bool, expected_text: str) -> dict:
    identifier(attempt, "attempt id")
    link = read_json(project / ".vercel/project.json")
    vercel_project = identifier(link.get("projectId"), "Vercel project")
    argv = ["vercel", "deploy", "--target", target, "--yes"]
    if store.config.dry_run:
        return {"status": "preview", "preferred_flow": "Git-linked deployment of the reviewed commit, then verify", "fallback_argv": argv,
                "baseline_required": baseline_id, "vercel_project": vercel_project, **evidence}
    require_approval(confirm, "PRODUCTION" if target == "production" else "PREVIEW")
    if target == "production" and not production_approved:
        raise CourseError("PRODUCTION_APPROVAL_REQUIRED", "Production needs separate action-time approval and --production-approved.")
    baseline = provider.deployment(baseline_id)
    if baseline["project_id"] != vercel_project or baseline["ready_state"] != "READY":
        raise CourseError("EXISTING_DEPLOYMENT_REQUIRED", "The instructor must provision and verify this project's first deployment. A new project's first deployment can be production.")
    if not shutil.which("vercel"):
        raise CourseError("DEPENDENCY_MISSING", "Install and authenticate the Vercel CLI; do not pass credentials as CLI arguments.")
    journal = store.root / "deployment-attempts" / (attempt + ".json")
    if journal.exists():
        raise CourseError("ATTEMPT_EXISTS", "Do not submit this deployment again. Read the local attempt, recover the provider id/URL, then use verify.")
    run = Run(store, "vercel-deploy", "Submit an explicitly approved deployment")
    run.save("running")  # Prove persistence is available before an external side effect.
    state = {"attempt": attempt, "status": "outcome_unknown", "run_id": run.id, "target": target, **evidence}
    write_json(journal, state)
    try:
        result = subprocess.run(argv, cwd=project, capture_output=True, text=True, timeout=300, shell=False)
        state["exit_code"] = result.returncode
        if result.returncode != 0:
            raise CourseError("SUBMISSION_UNCONFIRMED", "CLI did not report success. Recover the provider outcome before retrying; raw logs were not persisted.")
        host = deployment_host(result.stdout.strip())
        state.update(status="submitted", deployment_url="https://" + host)
        write_json(journal, state)
        run.event("submitted", {"deployment_url": "https://" + host, "target": target})
        run.save("partial")
    except (subprocess.SubprocessError, OSError, CourseError) as exc:
        write_json(journal, state)
        run.event("submission_unconfirmed", {"local_attempt": attempt})
        run.save("partial")
        if isinstance(exc, CourseError):
            raise
        raise CourseError("SUBMISSION_UNCONFIRMED", "Submission timed out or failed. The local attempt is durable; recover via provider readback, never blind resubmission.") from None
    return verify(store, provider, evidence, host, vercel_project, target, expected_text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    p.add_argument("--vercel-token-file", type=Path)
    p.add_argument("--team-id")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("verify", "deploy"):
        s = sub.add_parser(name)
        s.add_argument("--project", type=Path, required=True)
        s.add_argument("--project-id", default="course-site")
        s.add_argument("--test-id", required=True)
        s.add_argument("--expected-commit", required=True)
        s.add_argument("--expected-text", required=True)
        s.add_argument("--target", choices=("preview", "production"), default="preview")
        if name == "verify":
            s.add_argument("--deployment", required=True)
            s.add_argument("--vercel-project", required=True)
        else:
            s.add_argument("--baseline-deployment", required=True)
            s.add_argument("--attempt", required=True)
            s.add_argument("--confirm")
            s.add_argument("--production-approved", action="store_true")
    a = p.parse_args()
    store, provider = Store(Config.from_args(a)), Provider(a.vercel_token_file, a.team_id)
    evidence = gate(store, a.project, a.project_id, a.test_id, a.expected_commit)
    if a.command == "verify":
        result = verify(store, provider, evidence, a.deployment, a.vercel_project, a.target, a.expected_text)
    else:
        result = deploy(store, provider, a.project, evidence, a.target, a.baseline_deployment, a.attempt, a.confirm, a.production_approved, a.expected_text)
    emit(result)
    return 0 if result["status"] in {"preview", "verified"} else 1


if __name__ == "__main__":
    cli_main(main)
