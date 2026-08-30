import argparse
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from course_runtime import Config, CourseError, REPO, Store, digest, file_hash, read_json
from setup_course_skills import install


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


class LessonTwoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = Store(Config(state_dir=self.root / "state"))
        self.fixture = self.root / "fixture"
        shutil.copytree(REPO / "skills/course-support/examples/lesson-2", self.fixture)

    def scan(self):
        a = argparse.Namespace(folder=self.fixture / "incoming", rules=organizer.baseline.DEFAULT_RULES, include_low_confidence=False, dry_run=False)
        with contextlib.redirect_stdout(io.StringIO()):
            organizer.scan(a, self.store)
        return next((self.store.root / "organizer").glob("*-plan.json"))

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
