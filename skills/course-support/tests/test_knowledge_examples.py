"""Exercise the student-facing CLI against isolated synthetic source copies."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from course_runtime import REPO, file_hash

SEED = REPO / "skills/course-support/scripts/seed_demo.py"
KNOWLEDGE = REPO / "skills/personal-knowledge-capture/scripts/course_knowledge.py"
SCENARIOS = ("knowledge-study-notes", "knowledge-conflict-rules", "knowledge-weekly-update")


class KnowledgeExampleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.environment = {k: v for k, v in os.environ.items() if not k.startswith("PROMPTHON_")}

    def cli(self, script, *args, expected=0):
        result = subprocess.run([sys.executable, str(script), *map(str, args)],
                                cwd=REPO, env=self.environment, capture_output=True, text=True,
                                encoding="utf-8")
        self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def seed(self, scenario):
        folder = self.root / scenario
        self.cli(SEED, "--scenario", scenario, "--output", folder)
        return folder

    def knowledge(self, *args):
        return self.cli(KNOWLEDGE, "--storage", "local", "--state-dir", self.root / "state",
                        "--organization", "demo-org", "--workspace", "demo-student", *args)

    def hashes(self, folder):
        return {p.name: file_hash(p) for p in (folder / "research").iterdir()}

    def run_note(self, folder, note_id, *extra):
        before = self.hashes(folder)
        output = self.knowledge("synthesize", "--folder", folder / "research", "--note-id", note_id, *extra)
        self.assertEqual("succeeded", output["status"])
        self.assertEqual(before, self.hashes(folder), "Synthesis must preserve source content")
        saved = self.knowledge("show", "--note-id", note_id)
        self.assertEqual(output["revision"], saved["revision"])
        note = saved["data"]
        refs = {s["id"]: s for s in note["source_refs"]}
        rendered = Path(output["note_path"]).read_text(encoding="utf-8")
        for insight in note["key_insights"] + note["action_notes"]:
            self.assertIn(insight["source_id"], refs)
            self.assertIn(insight["text"], rendered)
            self.assertIn(insight["source_id"], rendered)
        for conflict in note["conflicts"]:
            for alternative in conflict["alternatives"]:
                for citation in alternative["citations"]:
                    source = refs[citation["source_id"]]
                    lines = (folder / "research" / source["source_ref"]).read_text(encoding="utf-8").splitlines()
                    self.assertIn(alternative["value"], lines[citation["line"] - 1])
        return output, note

    def test_seed_previews_and_preserves_existing_work(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                folder = self.root / scenario
                self.cli(SEED, "--scenario", scenario, "--output", folder, "--dry-run")
                self.assertFalse(folder.exists())
                self.seed(scenario)
                marker = json.loads((folder / ".course-demo.json").read_text())
                self.assertEqual(scenario, marker["scenario"])
                self.assertTrue(marker["synthetic"])
                source = next((folder / "research").iterdir())
                source.write_text("Synthetic student work to preserve.\n", encoding="utf-8")
                before = self.hashes(folder)
                result = self.cli(SEED, "--scenario", scenario, "--output", folder, expected=2)
                self.assertEqual("WOULD_OVERWRITE", result["error"])
                self.assertEqual(before, self.hashes(folder))

    def test_study_notes_deduplicate_without_losing_references(self):
        folder = self.seed("knowledge-study-notes")
        _, note = self.run_note(folder, "study-notes")
        self.assertEqual((3, 2, 1), (len(note["source_refs"]), note["unique_sources"], note["duplicates"]))
        self.assertEqual(2, len(note["key_insights"]))
        self.assertEqual(2, len(note["action_notes"]))
        self.assertEqual([], note["conflicts"])
        duplicate = next(s for s in note["source_refs"] if "duplicate_of" in s)
        representative = next(s for s in note["source_refs"] if s["id"] == duplicate["duplicate_of"])
        self.assertEqual(duplicate["text_hash"], representative["text_hash"])
        self.assertNotEqual(duplicate["source_ref"], representative["source_ref"])

    def test_custom_rules_add_budget_without_action_conflicts(self):
        folder = self.seed("knowledge-conflict-rules")
        rules_path = folder / "rules.json"
        shared = REPO / "skills/personal-knowledge-capture/references/synthesis-rules.json"
        original_shared_hash = file_hash(shared)
        first, before = self.run_note(folder, "conflict-notes", "--rules", rules_path)
        self.assertEqual({"capacity"}, {c["field"] for c in before["conflicts"]})
        rules = json.loads(rules_path.read_text())
        rules["single_value_fields"].append("budget")
        rules_path.write_text(json.dumps(rules), encoding="utf-8")
        second, after = self.run_note(folder, "conflict-notes", "--rules", rules_path)
        self.assertEqual(first["revision"] + 1, second["revision"])
        self.assertEqual({"capacity": {"20", "24"}, "budget": {"CAD 300", "CAD 450"}},
                         {c["field"]: {a["value"] for a in c["alternatives"]} for c in after["conflicts"]})
        self.assertEqual(before["action_notes"], after["action_notes"])
        self.assertEqual(2, len(after["action_notes"]))
        self.assertEqual((2, 0), (after["unique_sources"], after["duplicates"]))
        self.assertTrue(all(s["change"] == "unchanged" for s in after["source_refs"]))
        self.assertEqual(original_shared_hash, file_hash(shared))

    def test_weekly_update_distinguishes_saved_versions_from_changed_sources(self):
        folder = self.seed("knowledge-weekly-update")
        first, initial = self.run_note(folder, "weekly-update-notes")
        self.assertTrue(all(s["change"] == "new" for s in initial["source_refs"]))
        second, repeated = self.run_note(folder, "weekly-update-notes")
        self.assertTrue(all(s["change"] == "unchanged" for s in repeated["source_refs"]))
        self.assertEqual([s["sha256"] for s in initial["source_refs"]], [s["sha256"] for s in repeated["source_refs"]])
        changed = folder / "research/weekly-update.txt"
        changed.write_text(changed.read_text(encoding="utf-8").replace("Completed examples: 2", "Completed examples: 3"), encoding="utf-8")
        third, updated = self.run_note(folder, "weekly-update-notes")
        self.assertEqual([1, 2, 3], [o["revision"] for o in (first, second, third)])
        old_refs = {s["source_ref"]: s for s in initial["source_refs"]}
        for source in updated["source_refs"]:
            old = old_refs[source["source_ref"]]
            self.assertEqual(old["id"], source["id"])
            if source["source_ref"] == "weekly-update.txt":
                self.assertEqual("modified", source["change"])
                self.assertNotEqual(old["sha256"], source["sha256"])
            else:
                self.assertEqual("unchanged", source["change"])
                self.assertEqual(old["sha256"], source["sha256"])
        self.assertTrue(any("Completed examples: 3" in x["text"] for x in updated["key_insights"]))
        self.assertEqual((2, 0, []), (updated["unique_sources"], updated["duplicates"], updated["conflicts"]))


if __name__ == "__main__":
    unittest.main()
