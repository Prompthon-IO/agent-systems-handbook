import copy
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
for name in ("course-support", "business-data-structuring", "crm-operations", "business-data-analysis"):
    sys.path.insert(0, str(REPO / "skills" / name / "scripts"))
from course_runtime import Config, CourseError, Store, file_hash, read_json
from course_table import headers_normalized, normalize_cell, read_table, safe_csv_value
from structure_data import preview, apply as structure
from crm import plan, apply as operate
from analyze_data import analyze, run_analysis


class BusinessLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(Config(state_dir=self.root / "state"))
        self.source = REPO / "skills/business-data-structuring/examples/messy-pipeline.csv"
        self.schema = read_json(REPO / "skills/business-data-structuring/examples/schema.json")

    def request(self, name):
        return read_json(REPO / "skills/crm-operations/examples" / (name + ".json"))

    def apply_crm(self, name, high=False):
        request = self.request(name)
        proposed = plan(self.store, request)
        return operate(self.store, request, proposed["approval_sha256"], high)

    def test_csv_plan_clean_output_source_integrity_and_analysis_readback(self):
        before = file_hash(self.source)
        reviewed = preview(self.source, self.schema, dedupe=True)
        self.assertEqual({"input_rows": 6, "output_rows": 5, "columns": 7}, reviewed["shape"])
        self.assertEqual([], reviewed["errors"])
        self.assertEqual(1, len(reviewed["duplicates"]))
        dry = Store(Config(state_dir=self.root / "dry", dry_run=True))
        structure(dry, self.source, self.root / "clean", "pipeline", self.schema, None, dedupe=True)
        self.assertFalse((self.root / "clean").exists())
        self.assertFalse(dry.root.exists())
        with self.assertRaises(CourseError):
            structure(self.store, self.source, self.root / "clean", "pipeline", self.schema, "wrong", dedupe=True)
        result = structure(self.store, self.source, self.root / "clean", "pipeline", self.schema, reviewed["plan_sha256"], dedupe=True)
        self.assertEqual("succeeded", result["status"])
        self.assertEqual(before, file_hash(self.source))
        clean = self.root / "clean/clean.json"
        clean_before = file_hash(clean)
        report = run_analysis(self.store, clean, None, {})
        canonical = self.store.get("analysis_runs", report["analysis_id"])["data"]
        metrics = canonical["business_insights"]["metrics"]
        self.assertEqual("0.5", metrics["win_rate_closed_only"])
        self.assertEqual({"CAD": "4150.00"}, metrics["open_pipeline_by_currency"])
        self.assertEqual(1, canonical["data_quality"]["null_counts"]["contact_name"])
        self.assertEqual(clean_before, file_hash(clean))
        self.assertEqual(5, run_analysis(self.store, None, "pipeline", {})["overview"]["rows"])
        duplicate_report = run_analysis(self.store, self.source, None, self.schema)
        self.assertEqual("provisional", duplicate_report["business_insights"]["metric_status"])
        self.assertEqual("business-data-structuring", duplicate_report["business_insights"]["next_owner"])
        self.assertEqual({"CAD": "5350.00"}, duplicate_report["business_insights"]["metrics"]["open_pipeline_by_currency"])
        self.assertTrue(duplicate_report["key_patterns"]["numeric_summary_by_unit"]["deal_value"]["CAD"]["provisional"])
        with self.assertRaises(CourseError):
            structure(self.store, self.source, self.root / "clean", "pipeline", self.schema, reviewed["plan_sha256"], dedupe=True)

    def test_real_xlsx_ingest_formula_refusal_and_ambiguous_normalization(self):
        import openpyxl
        book = openpyxl.Workbook()
        with self.source.open(encoding="utf-8", newline="") as stream:
            for row in csv.reader(stream):
                book.active.append(row)
        xlsx = self.root / "fixture.xlsx"
        book.save(xlsx)
        before = file_hash(xlsx)
        self.assertEqual(preview(self.source, self.schema)["rows"], preview(xlsx, self.schema)["rows"])
        self.assertEqual("xlsx", preview(xlsx, self.schema)["source"]["format"])
        self.assertFalse(any("CSV" in item for item in preview(xlsx, self.schema)["assumptions"]))
        self.assertEqual(before, file_hash(xlsx))
        book.active["E2"] = "=1+1"
        book.save(self.root / "formula.xlsx")
        book.close()
        with self.assertRaises(CourseError) as failure:
            read_table(self.root / "formula.xlsx")
        self.assertEqual("FORMULA_INPUT", failure.exception.code)
        bad = copy.deepcopy(self.schema)
        bad["columns"]["close_date"]["format"] = "%Y-%m-%d"
        self.assertTrue(preview(self.source, bad)["errors"])
        self.assertEqual(["email", "email_2", "email_2_2"], headers_normalized(["Email", "Email", "Email 2"]))
        with self.assertRaises(ValueError):
            normalize_cell("USD 10", {"type": "currency", "currency": "CAD"})
        self.assertTrue(safe_csv_value('=HYPERLINK("synthetic")').startswith("'="))

    def test_all_crm_entities_audit_duplicate_resolution_and_stage_approval(self):
        contact = self.request("contact")
        draft = plan(self.store, contact)
        self.assertFalse((self.store.root / "course.sqlite").exists())
        with self.assertRaises(CourseError):
            operate(self.store, contact, None)
        for name in ("contact", "deal", "activity", "task"):
            saved = self.apply_crm(name)
            self.assertEqual(1, saved["audit_entries"])
            self.assertEqual(saved["run_id"], self.store.get(saved["collection"], saved["id"])["data"]["audit"][0]["run_id"])
        same_email = {"entity": "contact", "match": {"email": "ALEX@EXAMPLE.INVALID"}, "patch": {"company": "Maple Demo"}}
        resolved = plan(self.store, same_email)
        self.assertEqual("contact-demo-alex", resolved["id"])
        self.assertTrue(resolved["no_change"])
        close = self.request("close-deal")
        proposed = plan(self.store, close)
        self.assertTrue(proposed["high_impact"])
        with self.assertRaises(CourseError) as failure:
            operate(self.store, close, proposed["approval_sha256"])
        self.assertEqual("HIGH_IMPACT_APPROVAL_REQUIRED", failure.exception.code)
        self.assertEqual("lead", self.store.get("crm_deals", "deal-demo-workshop")["data"]["stage"])
        done = operate(self.store, close, proposed["approval_sha256"], True)
        self.assertEqual(2, done["audit_entries"])
        self.assertEqual("won", self.store.get("crm_deals", done["id"])["data"]["stage"])
        duplicate = self.request("contact")
        duplicate["match"]["id"] = "another-contact"
        with self.assertRaises(CourseError) as failure:
            plan(self.store, duplicate)
        self.assertEqual("DUPLICATE_CONTACT", failure.exception.code)

    def test_activity_and_task_dates_are_validated_without_any_write(self):
        self.apply_crm("contact")
        self.apply_crm("deal")
        before = self.store.list("skill_runs")
        for kind, field in (("activity", "occurred_on"), ("task", "due_date")):
            for invalid in (None, 20260830, [], "2026-02-30", "20260830", "2026-08-30T09:00:00Z"):
                request = self.request(kind)
                request["patch"][field] = invalid
                with self.subTest(kind=kind, invalid=invalid), self.assertRaises(CourseError) as failure:
                    plan(self.store, request)
                self.assertEqual("INVALID_" + kind.upper(), failure.exception.code)
            request = self.request(kind)
            del request["patch"][field]
            with self.assertRaises(CourseError) as failure:
                plan(self.store, request)
            self.assertEqual("INVALID_" + kind.upper(), failure.exception.code)
        self.assertEqual(before, self.store.list("skill_runs"))
        self.assertEqual([], self.store.list("crm_activities"))
        self.assertEqual([], self.store.list("crm_tasks"))

    def test_existing_deal_cannot_be_moved_to_another_contact(self):
        self.apply_crm("contact")
        deal = self.apply_crm("deal")
        second = {"entity": "contact", "match": {"id": "contact-demo-second"},
                  "patch": {"name": "Second Demo", "email": "second@example.invalid"}}
        operate(self.store, second, plan(self.store, second)["approval_sha256"])
        before = self.store.get("crm_deals", deal["id"])
        runs_before = self.store.list("skill_runs")
        reassignment = {"entity": "deal", "match": {"id": deal["id"]}, "patch": {"contact_id": "contact-demo-second"}}
        with self.assertRaises(CourseError) as failure:
            operate(self.store, reassignment, "any-approval", True)
        self.assertEqual("ENTITY_MISMATCH", failure.exception.code)
        self.assertEqual(before, self.store.get("crm_deals", deal["id"]))
        self.assertEqual(runs_before, self.store.list("skill_runs"))

    def test_crm_rejects_stale_plan_system_fields_foreign_scope_and_real_workspace(self):
        self.apply_crm("contact")
        request = self.request("contact")
        request["patch"] = {"company": "Reviewed change"}
        stale = plan(self.store, request)
        another = copy.deepcopy(request)
        another["patch"] = {"company": "Concurrent change"}
        operate(self.store, another, plan(self.store, another)["approval_sha256"])
        with self.assertRaises(CourseError):
            operate(self.store, request, stale["approval_sha256"])
        request["patch"] = {"audit": []}
        with self.assertRaises(CourseError):
            plan(self.store, request)
        other = Store(Config(state_dir=self.store.config.state_dir, workspace="other-student"))
        with self.assertRaises(CourseError):
            plan(other, self.request("deal"))
        class NotDemo(Store):
            def context(self, scope="course:read"):
                return {**super().context(scope), "environment": "course"}
        with self.assertRaises(CourseError):
            plan(NotDemo(self.store.config), self.request("contact"))

    def test_analysis_never_blends_currencies_or_claims_an_empty_denominator(self):
        data = {"grain": "one deal", "columns": [{"name": "stage", "type": "text"}, {"name": "value", "type": "currency", "currency": "CAD"}, {"name": "currency", "type": "text"}],
                "rows": [{"stage": "lead", "value": "100", "currency": "CAD"}, {"stage": "proposal", "value": "200", "currency": "USD"}]}
        result = analyze(data, {"synthetic": True})
        self.assertIsNone(result["business_insights"]["metrics"]["win_rate_closed_only"])
        self.assertEqual({"CAD": "100", "USD": "200"}, result["business_insights"]["metrics"]["open_pipeline_by_currency"])
        self.assertEqual({"CAD", "USD"}, set(result["key_patterns"]["numeric_summary_by_unit"]["value"]))


if __name__ == "__main__":
    unittest.main()
