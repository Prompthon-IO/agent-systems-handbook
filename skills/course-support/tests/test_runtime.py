import copy
import json
import sys
import tempfile
import threading
import unittest
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from course_runtime import Config, CourseError, Run, Store, digest


class ContractHandler(BaseHTTPRequestHandler):
    """Disposable HTTP contract fixture. It is not a production backend."""
    records = {}
    calls = []
    mode = "ok"

    def log_message(self, *args):
        pass

    def answer(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def allowed(self):
        self.calls.append((self.command, self.path))
        if self.headers.get("Authorization") != "Bearer synthetic-test-token":
            self.answer(401, {"error": "not_authenticated"})
            return False
        if not self.path.startswith("/api/organizations/demo-org/course/workspaces/student-a/"):
            self.answer(403, {"error": "tenant_mismatch"})
            return False
        return True

    def do_GET(self):
        if not self.allowed():
            return
        if self.path.endswith("/context"):
            if self.mode == "redirect":
                self.send_response(302)
                self.send_header("Location", "/credential-capture")
                self.end_headers()
                return
            if self.mode == "missing":
                self.answer(404, {})
                return
            self.answer(200, {"schema_version": 1, "organization_id": "demo-org", "workspace_id": "other" if self.mode == "tenant" else "student-a", "actor_id": "server-user", "environment": "production" if self.mode == "production" else "demo", "scopes": ["course:read", "course:write"]})
            return
        item = self.records.get(self.path)
        if item is None:
            self.answer(404, {})
            return
        item = copy.deepcopy(item)
        if self.mode == "different_readback":
            item["data"] = {"tampered": True}
        self.answer(200, item)

    def do_PUT(self):
        if not self.allowed():
            return
        if self.mode == "unavailable":
            self.answer(503, {"error": "a server error containing a pretend secret"})
            return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        old = self.records.get(self.path)
        if old and old["revision"] == body["expected_revision"] + 1 and old["data"] == body["data"]:
            self.answer(200, old)
            return
        if (old["revision"] if old else 0) != body["expected_revision"]:
            self.answer(409, {})
            return
        collection, record_id = self.path.rsplit("/", 2)[1:]
        record = {"organization_id": "demo-org", "workspace_id": "student-a", "actor_id": "server-user", "collection": collection, "id": record_id, "revision": body["expected_revision"] + 1, "created_at": "2026-08-30T12:00:00Z", "updated_at": "2026-08-30T12:00:00Z", "data": body["data"]}
        expected_key = digest(["PUT", f"/records/{collection}/{record_id}", body])
        if self.headers.get("Idempotency-Key") != expected_key:
            self.answer(422, {})
            return
        self.records[self.path] = record
        self.answer(200, record)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Config(state_dir=Path(self.tmp.name), workspace="student-a")

    def test_local_revision_idempotency_tenant_isolation_and_reset(self):
        a, b = Store(self.base), Store(replace(self.base, workspace="student-b"))
        first = a.put("crm_contacts", "contact-1", {"name": "Demo"})
        self.assertEqual(1, first["revision"])
        self.assertEqual(1, a.put("crm_contacts", "contact-1", {"name": "Demo"})["revision"])
        with self.assertRaises(CourseError) as conflict:
            a.put("crm_contacts", "contact-1", {"name": "Changed"})
        self.assertEqual("CONFLICT", conflict.exception.code)
        self.assertIsNone(b.maybe_get("crm_contacts", "contact-1"))
        b.put("crm_contacts", "contact-1", {"name": "Other student"})
        with self.assertRaises(CourseError):
            a.reset("student-b")
        self.assertEqual(1, a.reset()["records"])
        reset_preview = a.reset()
        self.assertEqual(1, sum(reset_preview["collections"].values()))
        self.assertEqual(1, len(reset_preview["affected_records"]))
        self.assertFalse(reset_preview["preview_truncated"])
        a.reset("student-a")
        self.assertEqual([], a.list("crm_contacts"))
        self.assertEqual("Other student", b.get("crm_contacts", "contact-1")["data"]["name"])

    def test_dry_run_creates_no_database_or_directories(self):
        root = Path(self.tmp.name) / "absent"
        store = Store(replace(self.base, dry_run=True, state_dir=root))
        record = Run(store, "sample-skill", "preview").save("previewed")
        self.assertTrue(record["dry_run"])
        self.assertFalse(root.exists())

    def test_url_and_identifier_boundaries(self):
        for url in ("http://example.com", "https://user:pass@example.com", "https://example.com?q=token", "https://example.com/path"):
            with self.subTest(url=url), self.assertRaises(CourseError):
                Store(replace(self.base, storage="prompthon", api_url=url))
        with self.assertRaises(CourseError):
            Store(replace(self.base, workspace="../other"))
        with self.assertRaises(CourseError):
            Store(self.base).put("social_campaigns", "parallel", {})


class HttpContractTests(RuntimeTests):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), ContractHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        super().setUp()
        ContractHandler.records, ContractHandler.calls, ContractHandler.mode = {}, [], "ok"
        token = Path(self.tmp.name) / "course-token"
        token.write_text("synthetic-test-token")
        self.remote = replace(self.base, storage="prompthon", api_url=f"http://127.0.0.1:{self.server.server_port}", token_file=token, allow_loopback=True)

    def test_write_then_get_exact_readback_and_server_actor(self):
        store = Store(self.remote)
        record = store.put("knowledge_notes", "weekly", {"summary": "Synthetic"})
        self.assertEqual("server-user", record["actor_id"])
        self.assertEqual("PUT", ContractHandler.calls[-2][0])
        self.assertEqual("GET", ContractHandler.calls[-1][0])
        self.assertEqual(1, store.put("knowledge_notes", "weekly", {"summary": "Synthetic"})["revision"])
        self.assertFalse((store.root / "course.sqlite").exists())

    def test_mismatch_does_not_report_success(self):
        ContractHandler.mode = "different_readback"
        with self.assertRaises(CourseError) as failure:
            Store(self.remote).put("knowledge_notes", "weekly", {"summary": "Synthetic"})
        self.assertEqual("READBACK_MISMATCH", failure.exception.code)

    def test_scope_production_redirect_and_missing_backend_fail_closed(self):
        for mode, code in (("tenant", "SCOPE_MISMATCH"), ("production", "SCOPE_MISMATCH"), ("redirect", "UNSAFE_REDIRECT"), ("missing", "BACKEND_NOT_READY")):
            ContractHandler.mode = mode
            with self.subTest(mode=mode), self.assertRaises(CourseError) as failure:
                Store(self.remote).context()
            self.assertEqual(code, failure.exception.code)
        self.assertFalse(any(path == "/credential-capture" for _, path in ContractHandler.calls))
        with self.assertRaises(CourseError):
            Store(replace(self.remote, workspace="student-b")).context()

    def test_error_sanitization_no_fallback_and_no_raw_secrets(self):
        ContractHandler.mode = "unavailable"
        store = Store(self.remote)
        with self.assertRaises(CourseError) as failure:
            store.put("knowledge_notes", "weekly", {"summary": "Synthetic"})
        self.assertEqual("UNAVAILABLE", failure.exception.code)
        self.assertNotIn("pretend secret", str(failure.exception))
        self.assertFalse((store.root / "course.sqlite").exists())
        ContractHandler.mode = "ok"
        for data in ({"api_token": "secret"}, {"source_ref": "/Users/example/private.txt"}, {"value": "postgresql://secret"}):
            with self.assertRaises(CourseError) as failure:
                store.put("knowledge_notes", "weekly", data)
            self.assertEqual("PRIVATE_DATA", failure.exception.code)


if __name__ == "__main__":
    unittest.main()
