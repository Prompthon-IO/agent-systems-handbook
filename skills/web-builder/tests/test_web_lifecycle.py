import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
for name in ("course-support", "web-builder", "webapp-testing", "vercel-deploy"):
    sys.path.insert(0, str(REPO / "skills" / name / "scripts"))
from course_runtime import Config, CourseError, Store, digest, file_hash, read_json, write_json
from web_builder import build, render
from web_project import source_manifest
from webapp_test import test_project as browser_test, serve, validate_suite
from course_deploy import Provider, deployment_host, deploy, gate, verify, prerequisites


class WebLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "site"
        self.store = Store(Config(state_dir=self.root / "state"))
        self.brief = read_json(REPO / "skills/web-builder/examples/workshop-brief.json")
        self.suite = read_json(REPO / "skills/webapp-testing/examples/workshop-suite.json")

    def build(self):
        return build(self.store, self.project, "course-site", self.brief, "BUILD")

    def test_preview_preserves_existing_stack_and_local_edits(self):
        dry = Store(Config(state_dir=self.root / "preview-state", dry_run=True))
        self.assertEqual("preview", build(dry, self.project, "course-site", self.brief, None)["status"])
        self.assertFalse(self.project.exists())
        self.assertFalse(dry.root.exists())
        self.build()
        index = self.project / "index.html"
        index.write_text(index.read_text() + "<!-- learner edit -->")
        before = file_hash(index)
        with self.assertRaises(CourseError):
            build(self.store, self.project, "course-site", self.brief, "BUILD", True)
        self.assertEqual(before, file_hash(index))
        custom = copy.deepcopy(self.brief)
        custom["constraints"].append("collect_real_payments")
        with self.assertRaises(CourseError):
            render(custom)
        bold = copy.deepcopy(self.brief)
        bold["style_direction"] = "bold-contrast"
        self.assertNotEqual(render(self.brief)["style.css"], render(bold)["style.css"])

    def test_invalid_suite_steps_fail_before_browser_or_state_creation(self):
        for step in (None, [], "click", {}, {"action": []}, {"action": "visible"}, {"action": "visible", "selector": " "}):
            with self.subTest(step=step), self.assertRaises(CourseError) as failure:
                validate_suite({"steps": [step]})
            self.assertEqual("INVALID_SUITE", failure.exception.code)
        self.assertFalse(self.store.root.exists())
        self.assertFalse(self.project.exists())

    def test_missing_or_invalid_provider_token_never_contacts_vercel(self):
        missing = self.root / "private-missing-token"
        invalid = self.root / "invalid-token"
        invalid.write_bytes(b"\xff\xfe")
        for token_file in (missing, invalid, self.root):
            provider = Provider(token_file)
            with self.subTest(token_file=token_file), patch.object(provider.opener, "open") as request:
                with self.assertRaises(CourseError) as failure:
                    provider.deployment("dpl_synthetic")
                self.assertEqual("PROVIDER_AUTH_REQUIRED", failure.exception.code)
                self.assertNotIn(str(token_file), str(failure.exception))
                request.assert_not_called()

    def test_real_browser_desktop_mobile_form_and_console_failure(self):
        self.build()
        before = source_manifest(self.project)
        result = browser_test(self.store, self.project, "course-site", self.suite)
        self.assertEqual("passed", result["status"], result)
        self.assertEqual(2, len(result["results"]))
        self.assertEqual(0, result["console_summary"]["error_count"])
        self.assertTrue(all((Path(result["evidence_dir"]) / x["screenshot"]["source_ref"]).is_file() for x in result["results"]))
        self.assertEqual(before, source_manifest(self.project))
        self.assertEqual("passed", self.store.get("web_test_runs", result["test_id"])["data"]["status"])
        app = self.project / "app.js"
        app.write_text(app.read_text() + '\nconsole.error("synthetic console failure");\n')
        failed = browser_test(self.store, self.project, "course-site", self.suite)
        self.assertEqual("failed", failed["status"])
        self.assertGreater(failed["console_summary"]["error_count"], 0)
        self.assertNotIn("synthetic console failure", json.dumps(failed))

    def test_static_server_denies_hidden_files_and_symlink_escape(self):
        import urllib.request
        import urllib.error
        self.build()
        (self.project / ".env.local").write_text("SYNTHETIC_SECRET")
        outside = self.root / "private.txt"
        outside.write_text("private")
        (self.project / "escape.txt").symlink_to(outside)
        with serve(self.project) as origin:
            for path in ("/.env.local", "/escape.txt"):
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(origin + path)
                self.assertEqual(403, error.exception.code)
                error.exception.close()

    def test_startup_refusal_is_terminal_and_offline_prerequisites_never_deploy(self):
        self.build()
        with patch("webapp_test.serve", side_effect=PermissionError("synthetic sandbox refusal")):
            with self.assertRaises(CourseError) as failure:
                browser_test(self.store, self.project, "course-site", self.suite)
            self.assertEqual("LOCAL_SERVER_UNAVAILABLE", failure.exception.code)
        run = self.store.list("skill_runs", 1)[0]["data"]
        self.assertEqual("failed", run["status"])
        self.assertIn("finished_at", run)
        with patch("course_deploy.Provider.deployment") as remote:
            result = prerequisites(self.store, self.project, "course-site", "missing-test")
            self.assertEqual("needs_setup", result["status"])
            self.assertFalse(result["provider_contacted"])
            self.assertFalse(result["deployed"])
            remote.assert_not_called()

    def test_failed_assertion_keeps_observed_text_only_in_local_diagnostics(self):
        self.build()
        suite = {"steps": [{"action": "text", "selector": "h1", "value": "deliberately wrong"}], "viewports": [{"width": 800, "height": 600}]}
        result = browser_test(self.store, self.project, "course-site", suite)
        self.assertEqual("failed", result["status"])
        detail = read_json(Path(result["evidence_dir"]) / result["results"][0]["local_diagnostics"]["source_ref"])
        self.assertEqual("deliberately wrong", detail["expected"])
        self.assertIn(self.brief["purpose"], detail["observed"])
        canonical = self.store.get("web_test_runs", result["test_id"])
        self.assertNotIn('"observed"', json.dumps(canonical))

    def test_deployment_requires_matching_sources_commit_and_provider_readback(self):
        self.build()
        fingerprint = digest(source_manifest(self.project))
        self.store.put("web_test_runs", "synthetic-test", {"project_id": "course-site", "status": "passed", "project_fingerprint": fingerprint})
        commit = "a" * 40
        with patch("course_deploy.git_commit", return_value=commit):
            evidence = gate(self.store, self.project, "course-site", "synthetic-test", commit)
            (self.project / "app.js").write_text("changed after test")
            with self.assertRaises(CourseError) as failure:
                gate(self.store, self.project, "course-site", "synthetic-test", commit)
            self.assertEqual("QA_REQUIRED", failure.exception.code)
        class FakeProvider:
            ready = "READY"
            sha = commit
            target = None
            page_status = "passed"
            def deployment(self, value):
                return {"deployment_id": "dpl_synthetic", "project_id": "prj_demo", "url": "synthetic-course.vercel.app", "ready_state": self.ready, "target": self.target, "commit_sha": self.sha}
            def url_readback(self, host, expected):
                return {"status": self.page_status}
        provider = FakeProvider()
        self.assertEqual("verified", verify(self.store, provider, evidence, "dpl_synthetic", "prj_demo", "preview", "demo")["status"])
        provider.ready = "BUILDING"
        self.assertEqual("unverified", verify(self.store, provider, evidence, "dpl_synthetic", "prj_demo", "preview", "demo")["status"])
        provider.ready, provider.page_status = "READY", "unverified"
        self.assertEqual("unverified", verify(self.store, provider, evidence, "dpl_synthetic", "prj_demo", "preview", "demo")["status"])
        for field, value in (("sha", "b" * 40), ("target", "production")):
            provider.sha, provider.target = commit, None
            setattr(provider, field, value)
            with self.assertRaises(CourseError):
                verify(self.store, provider, evidence, "dpl_synthetic", "prj_demo", "preview", "demo")
        for bad in ("http://synthetic.vercel.app", "https://vercel.app.evil.invalid", "https://user:pass@synthetic.vercel.app", "https://synthetic.vercel.app/?token=x"):
            with self.assertRaises(CourseError):
                deployment_host(bad)

    def test_no_submission_before_extra_production_approval_or_on_replay(self):
        self.build()
        write_json(self.project / ".vercel/project.json", {"projectId": "prj_demo"})
        provider = Provider()
        evidence = {"commit_sha": "a" * 40, "project_id": "course-site"}
        with patch.object(provider, "deployment", return_value={"project_id": "prj_demo", "ready_state": "READY"}) as remote, patch("course_deploy.subprocess.run") as command:
            with self.assertRaises(CourseError) as failure:
                deploy(self.store, provider, self.project, evidence, "production", "dpl_baseline", "demo-attempt", "PRODUCTION", False, "demo")
            self.assertEqual("PRODUCTION_APPROVAL_REQUIRED", failure.exception.code)
            remote.assert_not_called()
            command.assert_not_called()
            write_json(self.store.root / "deployment-attempts/demo-attempt.json", {"status": "outcome_unknown"})
            with patch("course_deploy.shutil.which", return_value="/test/vercel"):
                with self.assertRaises(CourseError) as failure:
                    deploy(self.store, provider, self.project, evidence, "preview", "dpl_baseline", "demo-attempt", "PREVIEW", False, "demo")
                self.assertEqual("ATTEMPT_EXISTS", failure.exception.code)
                command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
