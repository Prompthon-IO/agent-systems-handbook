#!/usr/bin/env python3
"""Run a declarative browser suite against a local site and persist evidence, not screenshots."""
from __future__ import annotations
import argparse
import contextlib
import functools
import http.server
import sys
import threading
import urllib.parse
import uuid
from pathlib import Path

for parent in Path(__file__).resolve().parents:
    shared = parent / "skills/course-support/scripts"
    if shared.is_dir():
        sys.path.insert(0, str(shared))
        sys.path.insert(0, str(parent / "skills/web-builder/scripts"))
        break
else:
    raise SystemExit("Install the course foundation (PR #222) before running this lesson.")
from course_runtime import Config, CourseError, Run, Store, add_storage_args, cli_main, digest, emit, file_hash, identifier, read_json, write_json
from web_project import source_manifest


def validate_suite(suite: dict) -> dict:
    if not isinstance(suite, dict) or not isinstance(suite.get("steps"), list) or not 1 <= len(suite["steps"]) <= 50:
        raise CourseError("INVALID_SUITE", "Provide a suite with 1–50 ordered browser checks.")
    for step in suite["steps"]:
        if step.get("action") not in {"visible", "fill", "click", "text", "url"}:
            raise CourseError("INVALID_SUITE", "Only visible/fill/click/text/url actions are supported; no arbitrary eval.")
        if step["action"] != "url" and not isinstance(step.get("selector"), str):
            raise CourseError("INVALID_SUITE", "A browser step needs a CSS selector.")
        if step["action"] in {"fill", "text", "url"} and not isinstance(step.get("value"), str):
            raise CourseError("INVALID_SUITE", "This browser step needs a string value.")
    viewports = suite.get("viewports", [{"width": 1280, "height": 800}])
    if not isinstance(viewports, list) or not 1 <= len(viewports) <= 3 or not all(isinstance(v, dict) and all(isinstance(v.get(k), int) and 240 <= v[k] <= 2400 for k in ("width", "height")) for v in viewports):
        raise CourseError("INVALID_SUITE", "Use 1–3 bounded viewports with width and height.")
    return suite


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        root = Path(self.directory).resolve()
        path = Path(self.translate_path(self.path))
        try:
            relative = path.relative_to(root)
        except ValueError:
            self.send_error(403)
            return None
        if not path.resolve().is_relative_to(root) or any(part.startswith(".") for part in relative.parts) or any(p.is_symlink() for p in (path, *path.parents) if p != root and p.is_relative_to(root)):
            self.send_error(403)
            return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(403)
        return None

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


@contextlib.contextmanager
def serve(project: Path):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(project.resolve())))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def run_browser(suite: dict, origin: str, evidence_dir: Path) -> dict:
    validate_suite(suite)
    target = urllib.parse.urlsplit(origin)
    if target.scheme != "http" or target.hostname not in {"127.0.0.1", "localhost", "::1"} or target.username or target.password or target.query or target.fragment:
        raise CourseError("UNSAFE_TARGET", "Classroom browser mutation tests accept only explicitly selected HTTP loopback sites.")
    try:
        from playwright.sync_api import sync_playwright, expect
    except ImportError:
        raise CourseError("DEPENDENCY_MISSING", "Install requirements.txt in the course venv, then run python -m playwright install chromium.") from None
    evidence_dir.mkdir(parents=True, exist_ok=True)
    results, console_errors, blocked = [], [], []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception:
            raise CourseError("BROWSER_UNAVAILABLE", "Install the pinned Chromium browser with python -m playwright install chromium; then rerun locally.") from None
        try:
            for index, viewport in enumerate(suite.get("viewports", [{"width": 1280, "height": 800}])):
                context = browser.new_context(viewport=viewport, service_workers="block")
                def route(request_route):
                    url = urllib.parse.urlsplit(request_route.request.url)
                    if (url.scheme, url.netloc) == (target.scheme, target.netloc) or url.scheme == "data":
                        request_route.continue_()
                    else:
                        blocked.append({"origin": url.scheme + "://" + url.netloc})
                        request_route.abort()
                context.route("**/*", route)
                def block_socket(socket):
                    blocked.append({"origin": "websocket_blocked"})
                    socket.close()
                context.route_web_socket("**/*", block_socket)
                page = context.new_page()
                page.set_default_timeout(5000)
                # Store error class/count/hash, not arbitrary console strings that may expose data.
                page.on("console", lambda msg: console_errors.append({"type": "console.error", "message_sha256": digest(msg.text)}) if msg.type == "error" else None)
                page.on("pageerror", lambda error: console_errors.append({"type": "pageerror", "message_sha256": digest(str(error))}))
                checks, failed_step, diagnostics = [], None, None
                try:
                    response = page.goto(origin, wait_until="networkidle", timeout=15000)
                    if response is None or not response.ok:
                        raise RuntimeError("page_http_error")
                    checks.append({"action": "open", "status": "passed", "http_status": response.status})
                    for number, step in enumerate(suite["steps"]):
                        failed_step = number
                        action = step["action"]
                        if action == "url":
                            expect(page).to_have_url(origin.rstrip("/") + step["value"])
                        else:
                            locator = page.locator(step["selector"])
                            if action == "visible":
                                expect(locator).to_be_visible()
                            elif action == "fill":
                                locator.fill(step["value"])
                            elif action == "click":
                                locator.click()
                            else:
                                expect(locator).to_contain_text(step["value"])
                        checks.append({"step": number, "action": action, "selector": step.get("selector"), "status": "passed"})
                    failed_step = None
                    # Delayed browser console errors also count as failures.
                    page.wait_for_timeout(100)
                except Exception as exc:
                    failed = suite["steps"][failed_step] if failed_step is not None else {"action": "open"}
                    detail = {"step": failed_step, "action": failed["action"], "selector": failed.get("selector"), "expected": failed.get("value"), "observed": None, "error_type": type(exc).__name__, "error_message": str(exc)[:1200]}
                    try:
                        detail["observed"] = page.url if failed["action"] in {"open", "url"} else page.locator(failed["selector"]).inner_text(timeout=1000)[:1200]
                    except Exception:
                        pass
                    diagnostic_file = evidence_dir / f"diagnostics-viewport-{index + 1}.json"
                    write_json(diagnostic_file, detail)  # Actual page text is local only; remote sees a reference.
                    diagnostics = {"source_ref": diagnostic_file.name, "sha256": file_hash(diagnostic_file)}
                    checks.append({"step": failed_step, "action": failed["action"], "selector": failed.get("selector"), "status": "failed", "error_type": type(exc).__name__})
                screenshot = evidence_dir / f"viewport-{index + 1}.png"
                try:
                    page.screenshot(path=str(screenshot), full_page=True)
                    evidence = {"source_ref": screenshot.name, "sha256": file_hash(screenshot)}
                except Exception:
                    checks.append({"status": "failed", "error_type": "screenshot_failed"})
                    evidence = None
                results.append({"viewport": viewport, "checks": checks, "failed_step": failed_step,
                                "status": "failed" if any(c["status"] == "failed" for c in checks) else "passed", "screenshot": evidence, "local_diagnostics": diagnostics})
                context.close()
        finally:
            browser.close()
    status = "failed" if console_errors or blocked or any(r["status"] == "failed" for r in results) else "passed"
    return {"status": status, "results": results, "console_summary": {"error_count": len(console_errors), "errors": console_errors[:100]}, "blocked_external_requests": blocked[:100]}


def test_project(store: Store, project: Path, project_id: str, suite: dict, url: str | None = None) -> dict:
    identifier(project_id, "project id")
    validate_suite(suite)
    files = source_manifest(project)
    if store.config.dry_run:
        return {"status": "preview", "project_id": project_id, "suite": suite, "project_fingerprint": digest(files)}
    run = Run(store, "webapp-testing", "Verify local browser flows and capture evidence")
    run.save("running")
    test_id = str(uuid.uuid4())
    evidence_dir = store.root / "web-evidence" / test_id
    try:
        with contextlib.nullcontext(url) if url else serve(project) as origin:
            result = run_browser(suite, origin, evidence_dir)
    except (CourseError, OSError) as exc:
        error = exc if isinstance(exc, CourseError) else CourseError("LOCAL_SERVER_UNAVAILABLE", "Local browser/server startup was refused. Use an authorized local runtime that permits loopback listening; do not change the test into a simulated pass.")
        run.event("browser_unavailable", {"error": error.code})
        run.save("failed")
        raise error from None
    if source_manifest(project) != files:
        result["status"] = "failed"
        result["source_changed_during_test"] = True
    data = {"test_id": test_id, "project_id": project_id, "project_fingerprint": digest(files), "suite": suite, **result}
    store.put("web_test_runs", test_id, data)
    run.artifact("browser_test", "Canonical browser evidence", {"test_id": test_id, "project_id": project_id, "status": result["status"], "project_fingerprint": digest(files)})
    run.save("succeeded" if result["status"] == "passed" else "failed")
    return {"status": result["status"], "run_id": run.id, "test_id": test_id, "evidence_dir": str(evidence_dir), "project_fingerprint": digest(files), "results": result["results"], "console_summary": result["console_summary"], "blocked_external_requests": result["blocked_external_requests"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    p.add_argument("--project", type=Path, required=True)
    p.add_argument("--project-id", default="course-site")
    p.add_argument("--suite", type=Path, required=True)
    p.add_argument("--url", help="Optional running loopback server; otherwise serve the static project temporarily.")
    a = p.parse_args()
    result = test_project(Store(Config.from_args(a)), a.project, a.project_id, read_json(a.suite), a.url)
    emit(result)
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    cli_main(main)
