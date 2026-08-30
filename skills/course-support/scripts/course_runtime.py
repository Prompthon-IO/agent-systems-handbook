"""Shared course persistence. No production DB driver, credentials or auth issuer.

Remote endpoints are a versioned BACKEND DEPENDENCY, not a deployed service.
The server must implement references/backend-contract.md before remote use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
if REPO.name == ".agents":
    REPO = REPO.parent  # Generated discovery copies still use the canonical repository and state root.
COLLECTIONS = frozenset({
    "skill_runs", "knowledge_sources", "knowledge_notes", "workflow_definitions",
    "web_projects", "web_test_runs", "deployment_records", "business_datasets",
    "crm_contacts", "crm_deals", "crm_activities", "crm_tasks", "analysis_runs",
    "content_strategies", "aeo_audits",
})
RUN_STATUSES = {"running", "previewed", "awaiting_approval", "succeeded", "failed", "partial"}
MAX_BYTES = 512_000


class CourseError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code, self.retryable = code, retryable


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def identifier(value: str, label: str = "identifier") -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", value):
        raise CourseError("INVALID_INPUT", f"Invalid {label}; use letters, digits, dot, underscore or hyphen.")
    return value


def canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CourseError("INVALID_INPUT", "Payload must be finite JSON data.") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path | str) -> Any:
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise CourseError("PAYLOAD_TOO_LARGE", "JSON input exceeds the course payload limit.")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def require_approval(actual: str | None, expected: str) -> None:
    if actual != expected:
        raise CourseError("APPROVAL_REQUIRED", f"Review the preview, then explicitly supply --confirm {expected}.")


def check_remote_payload(value: Any) -> None:
    """Fail closed on obvious credentials/absolute paths; not a general DLP service."""
    if isinstance(value, dict):
        for key, child in value.items():
            if re.search(r"(^|_)(token|password|secret|authorization|database_url|cookie)($|_)", key.lower()):
                raise CourseError("PRIVATE_DATA", "Credential fields must never be persisted.")
            check_remote_payload(child)
    elif isinstance(value, list):
        for child in value:
            check_remote_payload(child)
    elif isinstance(value, str):
        if re.search(r"postgres(?:ql)?://|(?:/Users/|/home/)|[A-Za-z]:[\\/]", value):
            raise CourseError("PRIVATE_DATA", "Use relative source references; never persist DB URLs or home paths.")


def add_storage_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--storage", choices=("local", "prompthon"), default=os.getenv("PROMPTHON_STORAGE", "local"))
    parser.add_argument("--organization", default=os.getenv("PROMPTHON_COURSE_ORGANIZATION"))
    parser.add_argument("--workspace", default=os.getenv("PROMPTHON_COURSE_WORKSPACE"))
    parser.add_argument("--actor", default=None, help="Local demo identity only; remote actor comes from the server.")
    parser.add_argument("--state-dir", type=Path, default=REPO / ".local-state" / "course")
    parser.add_argument("--api-url", default=os.getenv("PROMPTHON_COURSE_API_URL"))
    parser.add_argument("--token-file", type=Path, default=os.getenv("PROMPTHON_COURSE_TOKEN_FILE"))
    parser.add_argument("--allow-loopback", action="store_true", help="Allow an explicit HTTP loopback contract-test server.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; no records, files or external writes.")


@dataclass(frozen=True)
class Config:
    storage: str = "local"
    organization: str = "demo-org"
    workspace: str = "demo-student"
    actor: str = "demo-student"
    state_dir: Path = REPO / ".local-state" / "course"
    api_url: str | None = None
    token_file: Path | None = None
    allow_loopback: bool = False
    dry_run: bool = False

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "Config":
        if args.storage == "prompthon" and (not args.organization or not args.workspace or args.actor):
            raise CourseError("INVALID_CONTEXT", "Remote mode requires organization/workspace and a server-resolved actor (no --actor).")
        return cls(args.storage, args.organization or "demo-org", args.workspace or "demo-student",
                   args.actor or "demo-student", Path(args.state_dir), args.api_url,
                   Path(args.token_file) if args.token_file else None, args.allow_loopback, args.dry_run)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward a course credential to a redirect target.


class Store:
    def __init__(self, config: Config):
        self.config = config
        identifier(config.organization, "organization")
        identifier(config.workspace, "workspace")
        identifier(config.actor, "actor")
        self._context: dict | None = None
        self._token: str | None = None
        self._opener = urllib.request.build_opener(NoRedirect())
        if config.storage not in {"local", "prompthon"}:
            raise CourseError("INVALID_INPUT", "Unknown storage mode.")
        if config.storage == "prompthon":
            url = urllib.parse.urlsplit(config.api_url or "")
            loopback = config.allow_loopback and url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost", "::1"}
            if (url.scheme != "https" and not loopback) or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
                raise CourseError("INVALID_URL", "API URL must be an HTTPS origin; HTTP requires explicit loopback testing.")

    @property
    def scope(self) -> tuple[str, str]:
        return self.config.organization, self.config.workspace

    @property
    def root(self) -> Path:
        return self.config.state_dir / self.config.organization / self.config.workspace

    @property
    def prefix(self) -> str:
        return f"/api/organizations/{self.config.organization}/course/workspaces/{self.config.workspace}"

    def _request(self, method: str, path: str, body: Any = None) -> Any:
        if self._token is None:
            self._token = (self.config.token_file.read_text().strip() if self.config.token_file else os.getenv("PROMPTHON_COURSE_TOKEN", "").strip())
        if not self._token or "\n" in self._token or "\r" in self._token:
            raise CourseError("AUTH_REQUIRED", "Obtain a scoped course token from the Web App owner; use a token file or environment variable.")
        headers = {"Authorization": "Bearer " + self._token, "Accept": "application/json"}
        data = None
        if body is not None:
            check_remote_payload(body)
            data = canonical(body).encode()
            if len(data) > MAX_BYTES:
                raise CourseError("PAYLOAD_TOO_LARGE", "Persist metadata or an approved summary, not raw files.")
            headers.update({"Content-Type": "application/json", "Idempotency-Key": digest([method, path, body])})
        request = urllib.request.Request(self.config.api_url.rstrip("/") + self.prefix + path, data=data, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=15) as response:
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise CourseError("INVALID_RESPONSE", "Response exceeds the contract size limit.")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            codes = {401: "AUTH_REQUIRED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT", 412: "CONFLICT", 422: "INVALID_INPUT", 429: "RATE_LIMITED", 501: "BACKEND_NOT_READY"}
            code = "UNSAFE_REDIRECT" if 300 <= exc.code < 400 else codes.get(exc.code, "UNAVAILABLE")
            status = exc.code
            exc.close()
            # Server error bodies may contain credentials, SQL or private records. Never echo them.
            raise CourseError(code, f"Course API returned HTTP {status}; no local fallback occurred.", retryable=status == 429 or status >= 500) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise CourseError("UNAVAILABLE", "Course API is unreachable; retain the local recovery journal and retry explicitly.", retryable=True) from None
        except (ValueError, UnicodeDecodeError):
            raise CourseError("INVALID_RESPONSE", "Course API did not return contract JSON.") from None

    def context(self, permission: str = "course:read") -> dict:
        if self._context is None:
            if self.config.storage == "local":
                self._context = {"schema_version": 1, "organization_id": self.config.organization,
                                 "workspace_id": self.config.workspace, "actor_id": self.config.actor,
                                 "environment": "demo", "scopes": ["course:read", "course:write", "course:reset"]}
            else:
                try:
                    self._context = self._request("GET", "/context")
                except CourseError as exc:
                    if exc.code == "NOT_FOUND":
                        raise CourseError("BACKEND_NOT_READY", "The course API is not provisioned. See the backend dependency; do not guess endpoints or auth.") from None
                    raise
        c = self._context
        if not isinstance(c, dict) or c.get("schema_version") != 1 or (c.get("organization_id"), c.get("workspace_id")) != self.scope or c.get("environment") not in {"demo", "course"}:
            raise CourseError("SCOPE_MISMATCH", "Server context must attest this exact demo/course organization and workspace.")
        identifier(c.get("actor_id"), "server actor")
        if self.config.storage == "prompthon":
            check_remote_payload(c)
        if not isinstance(c.get("scopes"), list) or permission not in c["scopes"]:
            raise CourseError("FORBIDDEN", f"The course context lacks {permission}.")
        return c

    @contextmanager
    def _connect(self):
        self.root.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.root / "course.sqlite", timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("""CREATE TABLE IF NOT EXISTS course_records (
            organization_id TEXT NOT NULL, workspace_id TEXT NOT NULL, actor_id TEXT NOT NULL,
            collection TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, data_json TEXT NOT NULL,
            PRIMARY KEY (organization_id, workspace_id, collection, id))""")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _key(self, collection: str, record_id: str | None = None) -> None:
        if collection not in COLLECTIONS:
            raise CourseError("INVALID_INPUT", "Unknown course collection; social records use the existing Social API.")
        if record_id is not None:
            identifier(record_id, "record id")

    def _verify(self, record: Any, collection: str, record_id: str | None = None) -> dict:
        if not isinstance(record, dict) or (record.get("organization_id"), record.get("workspace_id")) != self.scope or record.get("collection") != collection or (record_id is not None and record.get("id") != record_id):
            raise CourseError("SCOPE_MISMATCH", "Record readback did not match the requested tenant, collection and id.")
        identifier(record.get("actor_id"), "record actor")
        identifier(record.get("id"), "record id")
        if self.config.storage == "prompthon":
            check_remote_payload(record)
        if not isinstance(record.get("revision"), int) or record["revision"] < 1 or "data" not in record or not record.get("created_at") or not record.get("updated_at"):
            raise CourseError("INVALID_RESPONSE", "Record readback lacks revision, content or timestamps.")
        return record

    @staticmethod
    def _row(row: sqlite3.Row) -> dict:
        result = dict(row)
        result["data"] = json.loads(result.pop("data_json"))
        return result

    def get(self, collection: str, record_id: str) -> dict:
        self._key(collection, record_id)
        self.context()
        if self.config.storage == "prompthon":
            record = self._request("GET", f"/records/{collection}/{record_id}")
        else:
            if not (self.root / "course.sqlite").exists():
                raise CourseError("NOT_FOUND", "No record in this workspace.")
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM course_records WHERE organization_id=? AND workspace_id=? AND collection=? AND id=?", (*self.scope, collection, record_id)).fetchone()
            if row is None:
                raise CourseError("NOT_FOUND", "No record in this workspace.")
            record = self._row(row)
        return self._verify(record, collection, record_id)

    def maybe_get(self, collection: str, record_id: str) -> dict | None:
        try:
            return self.get(collection, record_id)
        except CourseError as exc:
            if exc.code == "NOT_FOUND":
                return None
            raise

    def list(self, collection: str, limit: int = 20) -> list[dict]:
        self._key(collection)
        self.context()
        if not 1 <= limit <= 500:
            raise CourseError("INVALID_INPUT", "Limit must be between 1 and 500.")
        if self.config.storage == "prompthon":
            result = self._request("GET", f"/records/{collection}?limit={limit}")
            if not isinstance(result, dict) or not isinstance(result.get("items"), list):
                raise CourseError("INVALID_RESPONSE", "List response requires items.")
            records = result["items"]
        elif not (self.root / "course.sqlite").exists():
            records = []
        else:
            with self._connect() as conn:
                records = [self._row(r) for r in conn.execute("SELECT * FROM course_records WHERE organization_id=? AND workspace_id=? AND collection=? ORDER BY updated_at DESC, id LIMIT ?", (*self.scope, collection, limit)).fetchall()]
        return [self._verify(r, collection) for r in records]

    def put(self, collection: str, record_id: str, data: dict, *, expected_revision: int = 0) -> dict:
        self._key(collection, record_id)
        context = self.context("course:write")
        if not isinstance(data, dict) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise CourseError("INVALID_INPUT", "Record data must be an object and revision a non-negative integer.")
        encoded = canonical(data)
        if len(encoded.encode()) > MAX_BYTES:
            raise CourseError("PAYLOAD_TOO_LARGE", "Use an artifact reference instead of a large payload.")
        if self.config.storage == "prompthon":
            check_remote_payload(data)
        if self.config.dry_run:
            return {"id": record_id, "collection": collection, "data": data, "revision": expected_revision,
                    "dry_run": True, **{k: context[k] for k in ("organization_id", "workspace_id", "actor_id")}}
        if self.config.storage == "prompthon":
            ack = self._verify(self._request("PUT", f"/records/{collection}/{record_id}", {"schema_version": 1, "expected_revision": expected_revision, "data": data}), collection, record_id)
            if ack["actor_id"] != context["actor_id"]:
                raise CourseError("SCOPE_MISMATCH", "Write acknowledgement has a different actor.")
        else:
            stamp = now()
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                old = conn.execute("SELECT * FROM course_records WHERE organization_id=? AND workspace_id=? AND collection=? AND id=?", (*self.scope, collection, record_id)).fetchone()
                # Retrying identical data is idempotent, including after an uncertain acknowledgement.
                if old and old["revision"] == expected_revision + 1 and old["data_json"] == encoded and old["actor_id"] == context["actor_id"]:
                    pass
                elif (old["revision"] if old else 0) != expected_revision:
                    raise CourseError("CONFLICT", "Record changed. Read the latest revision and review before retrying.")
                else:
                    conn.execute("INSERT OR REPLACE INTO course_records VALUES (?,?,?,?,?,?,?,?,?)", (*self.scope, context["actor_id"], collection, record_id, expected_revision + 1, old["created_at"] if old else stamp, stamp, encoded))
            ack = self.get(collection, record_id)
        record = self.get(collection, record_id)
        if record["revision"] != ack["revision"] or record["revision"] != expected_revision + 1 or canonical(record["data"]) != encoded or record["actor_id"] != context["actor_id"]:
            raise CourseError("READBACK_MISMATCH", "Write may have succeeded, but canonical readback differs. Inspect the record before retrying.")
        return record

    def reset(self, confirm: str | None = None) -> dict:
        c = self.context("course:reset")
        if confirm is not None and not self.config.dry_run:
            require_approval(confirm, self.config.workspace)
        if c["environment"] != "demo":
            raise CourseError("FORBIDDEN", "Reset is restricted to server-attested demo workspaces.")
        if self.config.storage == "prompthon":
            if confirm is None or self.config.dry_run:
                return self._request("GET", "/reset-preview")
            require_approval(confirm, self.config.workspace)
            result = self._request("POST", "/reset", {"confirmation": confirm})
            if not isinstance(result, dict) or (result.get("organization_id"), result.get("workspace_id")) != self.scope:
                raise CourseError("SCOPE_MISMATCH", "Reset acknowledgement scope mismatch.")
            if any(self.list(collection, 1) for collection in COLLECTIONS):
                raise CourseError("READBACK_MISMATCH", "Reset did not clear all course records.")
            return result
        count = 0
        if (self.root / "course.sqlite").exists():
            with self._connect() as conn:
                count = conn.execute("SELECT count(*) FROM course_records WHERE organization_id=? AND workspace_id=?", self.scope).fetchone()[0]
                if confirm is not None and not self.config.dry_run:
                    require_approval(confirm, self.config.workspace)
                    conn.execute("DELETE FROM course_records WHERE organization_id=? AND workspace_id=?", self.scope)
        return {"organization_id": self.scope[0], "workspace_id": self.scope[1], "records": count,
                "status": "reset" if confirm and not self.config.dry_run else "preview", "local_files_removed": False}


class Run:
    def __init__(self, store: Store, skill: str, summary: str, *, run_id: str | None = None):
        self.store = store
        self.id = identifier(run_id or str(uuid.uuid4()))
        self.revision = 0
        self.data = {"schema_version": 1, "skill_name": identifier(skill), "run_id": self.id,
                     "status": "running", "created_at": now(), "updated_at": now(), "input_summary": summary[:1000],
                     "metadata": {}, "events": [], "artifacts": [], "source_refs": []}

    def event(self, event_type: str, payload: dict) -> None:
        self.data["events"].append({"id": str(uuid.uuid4()), "run_id": self.id, "event_type": event_type, "payload": payload, "created_at": now()})

    def artifact(self, artifact_type: str, title: str, content: Any, source_ref: str = "") -> None:
        self.data["artifacts"].append({"id": str(uuid.uuid4()), "run_id": self.id, "artifact_type": artifact_type,
                                       "title": title, "content_json": content, "source_ref": source_ref, "created_at": now()})

    def save(self, status: str) -> dict:
        if status not in RUN_STATUSES:
            raise CourseError("INVALID_INPUT", "Unknown run status.")
        self.data.update(status=status, updated_at=now())
        if status in {"succeeded", "failed", "partial"}:
            self.data["finished_at"] = now()
        record = self.store.put("skill_runs", self.id, self.data, expected_revision=self.revision)
        self.revision = record["revision"]
        return record


def cli_main(main) -> None:
    try:
        code = main()
    except CourseError as exc:
        emit({"error": exc.code, "message": str(exc), "retryable": exc.retryable})
        raise SystemExit(2) from None
    except (ValueError, OSError) as exc:
        # Avoid printing raw filesystem paths or externally supplied error content.
        emit({"error": "INVALID_INPUT", "message": type(exc).__name__ + ": check input files and permissions."})
        raise SystemExit(2) from None
    raise SystemExit(code or 0)
