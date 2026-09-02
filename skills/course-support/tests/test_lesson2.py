import argparse
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from course_runtime import Config, CourseError, REPO, Store, digest, file_hash, read_json
from setup_course_skills import install
from test_runtime import ContractHandler


def load(name, relative):
    path = REPO / relative
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


organizer = load("course_organizer", "skills/local-document-organizer/scripts/course_organizer.py")
knowledge = load("course_knowledge", "skills/personal-knowledge-capture/scripts/course_knowledge.py")
workflow = load("course_workflow", "skills/personal-workflow-automation/scripts/workflow.py")
SEED_DEMO = REPO / "skills/course-support/scripts/seed_demo.py"


class LessonTwoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = Store(Config(state_dir=self.root / "state"))
        self.fixture = self.root / "fixture"
        shutil.copytree(REPO / "skills/course-support/examples/lesson-2", self.fixture)

    def seed_demo(self, scenario, output, *, dry_run=False):
        command = [sys.executable, str(SEED_DEMO), "--scenario", scenario, "--output", str(output)]
        if dry_run:
            command.append("--dry-run")
        return subprocess.run(command, capture_output=True, text=True)

    def scan(self, fixture=None):
        a = argparse.Namespace(folder=(fixture or self.fixture) / "incoming", rules=organizer.baseline.DEFAULT_RULES, include_low_confidence=False, dry_run=False)
        with contextlib.redirect_stdout(io.StringIO()):
            organizer.scan(a, self.store)
        return next((self.store.root / "organizer").glob("*-plan.json"))

    def scenario_plan(self, scenario):
        fixture = self.root / scenario
        seeded = self.seed_demo(scenario, fixture)
        self.assertEqual(0, seeded.returncode, seeded.stderr or seeded.stdout)
        plan_path = self.scan(fixture)
        plan = read_json(plan_path)
        root = Path(plan["folder"])
        moves = {Path(item["old_path"]).name: Path(item["new_path"]).relative_to(root).as_posix()
                 for item in plan["suggestions"]}
        skipped = {Path(item["path"]).name for item in plan["skipped"]}
        return fixture, plan_path, moves, skipped

    def test_seed_demo_supports_organizer_scenarios_safely(self):
        scenarios = ("organizer-student-files", "organizer-freelancer-rules", "organizer-safe-recovery")
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                dry_output = self.root / f"{scenario}-dry-run"
                dry_run = self.seed_demo(scenario, dry_output, dry_run=True)
                self.assertEqual(0, dry_run.returncode, dry_run.stderr or dry_run.stdout)
                self.assertFalse(dry_output.exists())

                output = self.root / f"{scenario}-seeded"
                seeded = self.seed_demo(scenario, output)
                self.assertEqual(0, seeded.returncode, seeded.stderr or seeded.stdout)
                self.assertEqual({"synthetic": True, "lesson": 2, "scenario": scenario},
                                 read_json(output / ".course-demo.json"))

                repeated = self.seed_demo(scenario, output)
                self.assertEqual(2, repeated.returncode)
                self.assertEqual("WOULD_OVERWRITE", json.loads(repeated.stdout)["error"])

    def test_organizer_student_files_suggestions(self):
        fixture, _, moves, skipped = self.scenario_plan("organizer-student-files")
        self.assertEqual({
            "tuition-invoice.txt": "Invoices/tuition-invoice.txt",
            "school-reading.md": "School/school-reading.md",
            "internship-resume.txt": "Resumes/internship-resume.txt",
        }, moves)
        self.assertIn("random-download.zzz", skipped)
        self.assertTrue((fixture / "incoming/random-download.zzz").is_file())

    def test_organizer_freelancer_default_rule_suggestions(self):
        _, _, moves, _ = self.scenario_plan("organizer-freelancer-rules")
        self.assertEqual({
            "client-invoice-2026-09.txt": "Invoices/client-invoice-2026-09.txt",
            "client-service-agreement.md": "Contracts/client-service-agreement.md",
            "client-meeting-notes.txt": "Notes/client-meeting-notes.txt",
            "website-project-ideas.md": "Notes/website-project-ideas.md",
        }, moves)

    def test_organizer_safe_recovery_collision_apply_and_undo(self):
        fixture, plan_path, moves, skipped = self.scenario_plan("organizer-safe-recovery")
        incoming = fixture / "incoming"
        revised_invoice = incoming / "invoice-august.txt"
        reviewed_invoice = incoming / "Invoices/invoice-august.txt"
        revised_content = revised_invoice.read_text()
        reviewed_content = reviewed_invoice.read_text()
        self.assertEqual({
            "invoice-august.txt": "Invoices/invoice-august.txt",
            "coffee-receipt.txt": "Receipts/coffee-receipt.txt",
            "expense-notes.md": "Notes/expense-notes.md",
        }, moves)
        self.assertIn("mystery.zzz", skipped)

        with contextlib.redirect_stdout(io.StringIO()):
            result = organizer.apply(argparse.Namespace(plan=plan_path, confirm="ORGANIZE", dry_run=False), self.store)
        self.assertEqual(1, result)
        log = next((self.store.root / "organizer").glob("*-actions.json"))
        actions = {Path(item["old_path"]).name: item for item in read_json(log)["actions"]}
        self.assertEqual("conflict", actions["invoice-august.txt"]["status"])
        self.assertEqual("moved", actions["coffee-receipt.txt"]["status"])
        self.assertEqual("moved", actions["expense-notes.md"]["status"])
        self.assertEqual(revised_content, revised_invoice.read_text())
        self.assertEqual(reviewed_content, reviewed_invoice.read_text())
        self.assertFalse((incoming / "coffee-receipt.txt").exists())
        self.assertTrue((incoming / "Receipts/coffee-receipt.txt").is_file())
        self.assertFalse((incoming / "expense-notes.md").exists())
        self.assertTrue((incoming / "Notes/expense-notes.md").is_file())
        self.assertTrue((incoming / "mystery.zzz").is_file())

        with contextlib.redirect_stdout(io.StringIO()):
            organizer.undo(argparse.Namespace(log=log, dry_run=False, confirm="UNDO"), self.store)
        undone = {Path(item["old_path"]).name: item for item in read_json(log)["actions"]}
        self.assertNotIn("undo_status", undone["invoice-august.txt"])
        self.assertEqual("restored", undone["coffee-receipt.txt"]["undo_status"])
        self.assertEqual("restored", undone["expense-notes.md"]["undo_status"])
        self.assertTrue((incoming / "coffee-receipt.txt").is_file())
        self.assertTrue((incoming / "expense-notes.md").is_file())
        self.assertFalse((incoming / "Receipts/coffee-receipt.txt").exists())
        self.assertFalse((incoming / "Notes/expense-notes.md").exists())
        self.assertEqual(revised_content, revised_invoice.read_text())
        self.assertEqual(reviewed_content, reviewed_invoice.read_text())

    def test_organize_preview_approval_apply_undo_and_no_overwrite(self):
        source = self.fixture / "incoming"
        original = {p.name: file_hash(p) for p in source.iterdir()}
        plan = self.scan()
        self.assertIn("--confirm UNDO", plan.with_suffix(".md").read_text())
        self.assertEqual(original, {p.name: file_hash(p) for p in source.iterdir()})
        a = argparse.Namespace(plan=plan, confirm=None, dry_run=False)
        with self.assertRaises(CourseError):
            organizer.apply(a, self.store)
        a.confirm = "ORGANIZE"
        with contextlib.redirect_stdout(io.StringIO()):
            organizer.apply(a, self.store)
        log = next((self.store.root / "organizer").glob("*-actions.json"))
        actions = read_json(log)["actions"]
        self.assertGreater(len(actions), 0)
        self.assertTrue(all(x["status"] == "moved" for x in actions))
        self.assertTrue((source / "mystery.zzz").exists())
        with self.assertRaises(CourseError):
            organizer.apply(a, self.store)
        with contextlib.redirect_stdout(io.StringIO()):
            organizer.undo(argparse.Namespace(log=log, dry_run=False, confirm="UNDO"), self.store)
        self.assertEqual(original, {p.name: file_hash(p) for p in source.iterdir() if p.is_file()})

    def test_plan_edit_changed_file_and_collision_are_not_applied(self):
        plan_path = self.scan()
        plan = read_json(plan_path)
        collision = Path(plan["suggestions"][0]["new_path"])
        collision.parent.mkdir(parents=True)
        collision.write_text("never overwrite this")
        a = argparse.Namespace(plan=plan_path, confirm="ORGANIZE", dry_run=False)
        with contextlib.redirect_stdout(io.StringIO()):
            organizer.apply(a, self.store)
        self.assertEqual("never overwrite this", collision.read_text())
        plan["suggestions"][0]["new_path"] = str(self.root / "escape")
        plan_path.write_text(json.dumps(plan))
        with self.assertRaises(CourseError) as failure:
            organizer.checked_plan(plan_path, self.store)
        self.assertEqual("PLAN_CHANGED", failure.exception.code)

    def test_malformed_organizer_plans_never_move_files(self):
        original = {p.name: file_hash(p) for p in (self.fixture / "incoming").iterdir()}
        valid = read_json(self.scan())
        bad_path = self.root / "bad-plan.json"
        mutations = [[], None, {"folder": str(self.fixture)},
                     {**valid, "suggestions": [None]}, {**valid, "suggestions": [{}]},
                     {**valid, "run_id": "../../escape"}, {**valid, "skipped": ["wrong-shape"]}]
        for value in mutations:
            if isinstance(value, dict):
                value.pop("plan_sha256", None)
                value["plan_sha256"] = digest(value)
            bad_path.write_text(json.dumps(value))
            with self.subTest(value=value), self.assertRaises(CourseError):
                organizer.apply(argparse.Namespace(plan=bad_path, confirm="ORGANIZE", dry_run=False), self.store)
        self.assertEqual(original, {p.name: file_hash(p) for p in (self.fixture / "incoming").iterdir()})
        self.assertFalse(list((self.store.root / "organizer").glob("*-actions.json")))

    def test_remote_failure_after_move_leaves_local_undo(self):
        plan = self.scan()
        class FailsOnFinish(Store):
            calls = 0
            def put(self, *args, **kwargs):
                self.calls += 1
                if self.calls == 2:
                    raise CourseError("UNAVAILABLE", "synthetic failure")
                return super().put(*args, **kwargs)
        failing = FailsOnFinish(self.store.config)
        with contextlib.redirect_stdout(io.StringIO()):
            result = organizer.apply(argparse.Namespace(plan=plan, confirm="ORGANIZE", dry_run=False), failing)
        self.assertEqual(2, result)
        log = next((self.store.root / "organizer").glob("*-actions.json"))
        with contextlib.redirect_stdout(io.StringIO()):
            organizer.undo(argparse.Namespace(log=log, confirm="UNDO", dry_run=False), self.store)
        self.assertTrue((self.fixture / "incoming/invoice-demo.txt").exists())

    def test_knowledge_dedup_conflicts_incremental_and_source_integrity(self):
        folder = self.fixture / "research"
        before = {p.name: file_hash(p) for p in folder.iterdir()}
        sources, skipped = knowledge.collect(folder, self.store)
        note = knowledge.synthesize(sources, skipped)
        self.assertEqual((2, 1), (note["unique_sources"], note["duplicates"]))
        conflict = next(x for x in note["conflicts"] if x["field"] == "capacity")
        self.assertEqual({"capacity"}, {x["field"] for x in note["conflicts"]})
        self.assertTrue(all("Capacity:" in x["text"] for x in note["key_insights"]))
        self.assertEqual(2, len(note["action_notes"]))
        self.assertEqual({"20", "24"}, {x["value"] for x in conflict["alternatives"]})
        again, _ = knowledge.collect(folder, self.store)
        self.assertTrue(all(s["change"] == "unchanged" for s in again))
        self.assertEqual(before, {p.name: file_hash(p) for p in folder.iterdir()})
        self.assertTrue(all("text" not in s for s in note["source_refs"]))

    def test_workflow_approval_pause_resume_does_not_repeat_completed_step(self):
        counter = self.root / "counter.txt"
        step = [sys.executable, "-c", "from pathlib import Path;p=Path(" + repr(str(counter)) + ");p.write_text(p.read_text()+'x' if p.exists() else 'x')"]
        definition = {"id": "test-flow", "trigger": {"type": "manual"}, "steps": [
            {"id": "one", "argv": step, "approval_required": False, "retryable": False},
            {"id": "two", "argv": step, "approval_required": True, "retryable": False}]}
        with self.assertRaises(CourseError):
            workflow.execute(self.store, definition, "wrong", [])
        self.assertFalse(counter.exists())
        paused = workflow.execute(self.store, definition, digest(definition), [])
        self.assertEqual("awaiting_approval", paused["status"])
        self.assertEqual("x", counter.read_text())
        done = workflow.execute(self.store, definition, digest(definition), ["two"], previous_id=paused["run_id"])
        self.assertEqual("succeeded", done["status"])
        self.assertEqual("xx", counter.read_text())

    def test_corrupt_workflow_journal_cannot_skip_or_replay_steps(self):
        definition = {"id": "journal-check", "trigger": {"type": "manual"}, "steps": [
            {"id": "one", "argv": [sys.executable, "-c", "pass"], "approval_required": False, "retryable": False},
            {"id": "two", "argv": [sys.executable, "-c", "pass"], "approval_required": True, "retryable": False}]}
        paused = workflow.execute(self.store, definition, digest(definition), [])
        path = Path(paused["journal"])
        valid = read_json(path)
        variants = [None, {}, {**valid, "steps": valid["steps"][:1]},
                    {**valid, "steps": list(reversed(valid["steps"]))},
                    {**valid, "steps": [None, valid["steps"][1]]},
                    {**valid, "steps": [{"id": "one", "status": []}, valid["steps"][1]]},
                    {**valid, "run_id": "different-run"}]
        records_before = self.store.list("skill_runs")
        with patch.object(workflow.subprocess, "run") as child:
            for value in variants:
                path.write_text(json.dumps(value))
                with self.subTest(value=value), self.assertRaises(CourseError) as failure:
                    workflow.execute(self.store, definition, digest(definition), ["two"], previous_id=paused["run_id"])
                self.assertEqual("INVALID_JOURNAL", failure.exception.code)
            path.write_text('{"steps":')
            with self.assertRaises(CourseError) as failure:
                workflow.execute(self.store, definition, digest(definition), ["two"], previous_id=paused["run_id"])
            self.assertEqual("INVALID_JOURNAL", failure.exception.code)
            child.assert_not_called()
        self.assertEqual(records_before, self.store.list("skill_runs"))
        path.write_text(json.dumps(valid))
        self.assertEqual("succeeded", workflow.execute(self.store, definition, digest(definition), ["two"], previous_id=paused["run_id"])["status"])

    def test_remote_children_keep_scope_and_require_explicit_course_access(self):
        handler = type("WorkflowContract", (ContractHandler,), {"records": {}, "calls": [], "mode": "ok"})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        remote = Store(Config(storage="prompthon", workspace="student-a", state_dir=self.root / "remote",
                             api_url=f"http://127.0.0.1:{server.server_port}", allow_loopback=True))
        code = ("import argparse,os;from course_runtime import Config,Store,add_storage_args,cli_main;"
                "assert 'OTHER_SERVICE_TOKEN' not in os.environ and 'DATABASE_URL' not in os.environ;"
                "p=argparse.ArgumentParser();add_storage_args(p);"
                "cli_main(lambda: (Store(Config.from_args(p.parse_args())).put('knowledge_notes','child-note',{'text':'synthetic'}),None)[1])")
        definition = {"id": "remote-children", "trigger": {"type": "manual"}, "steps": [
            {"id": "child", "argv": ["{python}", "-c", code, "--allow-loopback", "--state-dir", "{state_dir}"],
             "approval_required": False, "retryable": False}]}
        try:
            with patch.dict(os.environ, {"PROMPTHON_COURSE_TOKEN": "synthetic-test-token", "OTHER_SERVICE_TOKEN": "never-forward",
                                         "DATABASE_URL": "never-forward", "PROMPTHON_COURSE_WORKSPACE": "wrong-env-workspace",
                                         "PYTHONPATH": str(REPO / "skills/course-support/scripts")}):
                blocked = workflow.execute(remote, definition, digest(definition), [])
                self.assertEqual("failed", blocked["status"])
                key = remote.prefix + "/records/knowledge_notes/child-note"
                self.assertNotIn(key, handler.records)
                definition["steps"][0]["inherit_course_access"] = True
                passed = workflow.execute(remote, definition, digest(definition), [])
                self.assertEqual("succeeded", passed["status"])
                saved = remote.get("knowledge_notes", "child-note")
                self.assertEqual(("student-a", "server-user", {"text": "synthetic"}), (saved["workspace_id"], saved["actor_id"], saved["data"]))
                self.assertFalse(list((self.root / "remote").rglob("*.sqlite*")))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_workflow_failure_stops_following_command(self):
        flag = self.root / "should-not-exist"
        definition = {"id": "fail-flow", "trigger": {"type": "manual"}, "steps": [
            {"id": "fail", "argv": [sys.executable, "-c", "raise SystemExit(3)"], "approval_required": False, "retryable": False},
            {"id": "later", "argv": [sys.executable, "-c", "open(" + repr(str(flag)) + ",'w').close()"], "approval_required": False, "retryable": True}]}
        failed = workflow.execute(self.store, definition, digest(definition), [])
        self.assertEqual("failed", failed["status"])
        self.assertFalse(flag.exists())
        with self.assertRaises(CourseError):
            workflow.execute(self.store, definition, digest(definition), [], previous_id=failed["run_id"])

    def test_cli_pause_is_not_a_success_exit(self):
        definition = {"id": "cli-pause", "trigger": {"type": "manual"}, "steps": [
            {"id": "gate", "argv": [sys.executable, "-c", "print('synthetic')"], "approval_required": True, "retryable": False}]}
        self.store.put("workflow_definitions", definition["id"], definition)
        result = subprocess.run([sys.executable, str(REPO / "skills/personal-workflow-automation/scripts/workflow.py"),
                                 "--state-dir", str(self.store.config.state_dir), "run", "--workflow", definition["id"],
                                 "--confirm", digest(definition)], capture_output=True, text=True)
        self.assertEqual(3, result.returncode, result.stderr)
        self.assertEqual("awaiting_approval", json.loads(result.stdout)["status"])

    def test_setup_preserves_edits_and_syncs_discovery_copies(self):
        repo = self.root / "clone"
        (repo / "skills").mkdir(parents=True)
        for name in ("local-document-organizer", "personal-knowledge-capture", "personal-workflow-automation", "course-support"):
            shutil.copytree(REPO / "skills" / name, repo / "skills" / name)
        self.assertEqual(3, len(install(repo, "2")["skills"]))
        self.assertTrue((repo / ".agents/skills/course-support/references/backend-contract.md").is_file())
        self.assertFalse((repo / ".agents/skills/course-support/SKILL.md").exists())
        installed_runtime = repo / ".agents/skills/course-support/scripts"
        check_root = subprocess.run([sys.executable, "-c", "import sys;sys.path.insert(0," + repr(str(installed_runtime)) + ");from course_runtime import REPO;print(REPO)"], capture_output=True, text=True, check=True)
        self.assertEqual(str(repo.resolve()), check_root.stdout.strip())
        self.assertNotIn("*", (repo / ".agents/.gitignore").read_text())
        install(repo, "2", check=True)
        installed = repo / ".agents/skills/personal-workflow-automation/SKILL.md"
        installed.write_text(installed.read_text() + "\nlocal edit\n")
        with self.assertRaises(CourseError) as failure:
            install(repo, "2")
        self.assertEqual("LOCAL_EDITS", failure.exception.code)
        install(repo, "2", replace=True)
        install(repo, "2", check=True)


if __name__ == "__main__":
    unittest.main()
