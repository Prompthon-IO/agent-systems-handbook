import copy
import html
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
for name in ("course-support", "content-strategy", "prompthon-social-campaign-manager", "ai-search-visibility"):
    sys.path.insert(0, str(REPO / "skills" / name / "scripts"))
from course_runtime import Config, CourseError, Store, file_hash, read_json, write_json
from strategy import compile_strategy, preview, save
from course_social import compile_plan, prepare
from aeo_audit import audit_site, run_audit


class MediaLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(Config(state_dir=self.root / "state", organization="00000000-0000-4000-8000-000000000001", api_url="https://course.example.invalid"))
        self.brief = read_json(REPO / "skills/content-strategy/examples/workshop-strategy.json")
        self.campaign = read_json(REPO / "skills/prompthon-social-campaign-manager/examples/course-campaign.json")
        self.spec = read_json(REPO / "skills/ai-search-visibility/examples/audit-spec.json")
        self.site = self.root / "site"
        shutil.copytree(REPO / "skills/ai-search-visibility/examples/site", self.site)

    def save_strategy(self):
        plan = preview(self.store, "workshop-strategy", self.brief, 0)
        return save(self.store, "workshop-strategy", self.brief, 0, plan["plan_sha256"])

    def test_strategy_priorities_calendar_revision_and_unvalidated_hypothesis(self):
        dry = Store(Config(state_dir=self.root / "dry", dry_run=True))
        save(dry, "workshop-strategy", self.brief, 0, None)
        self.assertFalse(dry.root.exists())
        first = self.save_strategy()
        self.assertEqual(1, first["revision"])
        self.assertEqual(4, len(first["content_calendar"]))
        self.assertTrue(all(x["status"] == "planned_not_scheduled" for x in first["content_calendar"]))
        compiled = self.store.get("content_strategies", "workshop-strategy")["data"]
        self.assertEqual({"searchable", "shareable"}, {t["intent"] for t in compiled["priority_topics"]})
        self.assertEqual("unvalidated_hypothesis", next(t for t in compiled["priority_topics"] if t["id"] == "practice-story")["validation_status"])
        revised = copy.deepcopy(self.brief)
        revised["topics"][3]["business_fit"] = 5
        plan = preview(self.store, "workshop-strategy", revised, 1)
        second = save(self.store, "workshop-strategy", revised, 1, plan["plan_sha256"])
        self.assertEqual(2, second["revision"])
        with self.assertRaises(CourseError):
            preview(self.store, "workshop-strategy", self.brief, 0)

    def test_social_preparation_reuses_payloads_and_creates_no_parallel_social_records(self):
        self.save_strategy()
        result = prepare(self.store, self.campaign)
        self.assertFalse(result["canonical_social_objects_created"])
        plan = read_json(result["plan_file"])
        self.assertEqual(1, plan["strategy_revision"])
        self.assertEqual(2, len(plan["posts"][0]["variantOverrides"]))
        self.assertNotEqual(plan["posts"][0]["variantOverrides"][0]["copyText"], plan["posts"][0]["variantOverrides"][1]["copyText"])
        self.assertEqual("previewed", self.store.get("skill_runs", result["run_id"])["data"]["status"])
        self.assertFalse(self.store.list("deployment_records"))
        bad = copy.deepcopy(self.campaign)
        bad["posts"][0]["providers"] = ["unknown-channel-uuid"]
        with self.assertRaises(CourseError):
            compile_plan(self.store, bad)
        other = Store(Config(state_dir=self.store.config.state_dir, workspace="other-student"))
        with self.assertRaises(CourseError):
            compile_plan(other, self.campaign)

    def test_browser_adapter_contract_with_all_network_mocked(self):
        self.save_strategy()
        result = prepare(self.store, self.campaign)
        node = shutil.which("node")
        self.assertTrue(node, "Node is required for the browser-adapter contract test")
        process = subprocess.run([node, str(REPO / "skills/prompthon-social-campaign-manager/tests/test_course_browser.cjs"), result["plan_file"]], capture_output=True, text=True, timeout=30)
        self.assertEqual(0, process.returncode, process.stderr)
        summary = json.loads(process.stdout)
        self.assertEqual(0, summary["real_network_requests"])
        self.assertTrue(summary["synthetic_only"])
        self.assertEqual(len(summary["checks"]), summary["cases"])
        self.assertIn("webcrypto-without-randomUUID", summary["checks"])
        self.assertIn("missing-secure-random-refused", summary["checks"])

    def test_aeo_extraction_conflict_evidence_and_same_scope_recheck(self):
        before = {p.name: file_hash(p) for p in self.site.iterdir()}
        first = run_audit(self.store, self.site, self.spec, "course-aeo", 0)
        codes = {f["code"] for f in first["findings"]}
        self.assertTrue({"answer_gap", "site_consistency", "entity_positioning", "evidence_attribution", "heading_structure"} <= codes)
        self.assertEqual(before, {p.name: file_hash(p) for p in self.site.iterdir()})
        conflict = next(f for f in first["findings"] if f["code"] == "site_consistency")
        self.assertEqual({"90 minutes", "120 minutes"}, {e["value"] for e in conflict["evidence"]})
        about = self.site / "about.html"
        about.write_text(about.read_text().replace("120 minutes", "90 minutes").replace("<h1>About the workshop</h1>", "<h1>Prompthon Course Studio</h1>").replace("<h3>", "<h2>").replace("</h3>", "</h2>"))
        index = self.site / "index.html"
        facts = (REPO / "skills/content-strategy/examples/synthetic-workshop-brief.md").read_text()
        build_fact = facts.split("Build deliverable: ", 1)[1].splitlines()[0]
        index.write_text(index.read_text().replace("</body>", "<h2>What will I build?</h2><p>" + html.escape(build_fact) + "</p></body>"))
        second = run_audit(self.store, self.site, self.spec, "course-aeo", 1)
        self.assertTrue(second["recheck"]["scope_comparable"])
        self.assertIn(conflict["id"], second["recheck"]["resolved"])
        self.assertNotIn("answer_gap", {f["code"] for f in second["findings"]})
        self.assertEqual(4, len(second["recheck"]["resolved"]))
        self.assertEqual({"evidence_attribution"}, {f["code"] for f in second["findings"]})
        self.assertEqual(2, self.store.get("aeo_audits", "course-aeo")["revision"])

    def test_invalid_audit_page_entries_never_create_records_or_modify_sources(self):
        before = {p.name: file_hash(p) for p in self.site.iterdir()}
        for entry in (None, [], "index.html", {}, {"path": 2, "url": "https://example.invalid"},
                      {"path": "", "url": "https://example.invalid"}, {"path": "index.html", "url": []}):
            bad = {**self.spec, "pages": [entry]}
            with self.subTest(entry=entry), self.assertRaises(CourseError) as failure:
                run_audit(self.store, self.site, bad, "invalid-audit", 0)
            self.assertEqual("INVALID_AUDIT", failure.exception.code)
        self.assertEqual(before, {p.name: file_hash(p) for p in self.site.iterdir()})
        self.assertEqual([], self.store.list("aeo_audits"))
        self.assertEqual([], self.store.list("skill_runs"))

    def test_audit_scope_change_is_not_claimed_as_resolution_and_rejects_escape(self):
        first = run_audit(self.store, self.site, self.spec, "course-aeo", 0)
        changed = copy.deepcopy(self.spec)
        changed["target_queries"] = changed["target_queries"][:1]
        second = run_audit(self.store, self.site, changed, "course-aeo", 1)
        self.assertFalse(second["recheck"]["scope_comparable"])
        self.assertEqual([], second["recheck"]["resolved"])
        self.assertTrue(second["recheck"]["removed_by_scope_change"])
        escaped = copy.deepcopy(self.spec)
        escaped["pages"][0]["path"] = "../outside.html"
        with self.assertRaises(CourseError):
            audit_site(self.site, escaped)


if __name__ == "__main__":
    unittest.main()
