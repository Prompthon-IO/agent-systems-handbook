# Course persistence contract v1

Status: proposed Web App dependency, implemented by the Handbook client and conformance tests only. Do not infer that these endpoints exist on any live origin. The backend must reuse Prompthon's current authenticated user and organization model; it must not resurrect the deprecated local bridge token flow.

## Trust boundary

Student Codex → HTTPS API with a short-lived scoped course bearer token → server-side Neon/PostgreSQL. The Web App owns token issuance/revocation, existing user/organization membership, workspace membership, tenant enforcement, migrations, rate limits and operations. The client never accepts a student-supplied remote actor, DB connection string, SQL, arbitrary collection, redirect or production context.

Every physical row in the proposed execution layer must carry `organization_id`, `workspace_id` and `actor_id`; foreign keys and reads must enforce the same tenant. Token scope is verified server-side for every operation. Organization/workspace strings in a URL are selectors, not authorization. Cross-tenant reads, writes, list pagination, relationship resolution and reset must return 403 or non-enumerating 404. The client performs a second scope check but cannot replace server enforcement.

Base prefix: `/api/organizations/{organization_id}/course/workspaces/{workspace_id}`. Header: `Authorization: Bearer <scoped-course-token>`. Exact paths below are relative to that prefix.

## Context

`GET /context` returns:

```json
{
  "schema_version": 1,
  "organization_id": "demo-org",
  "workspace_id": "student-01",
  "actor_id": "authenticated-user-id",
  "environment": "demo",
  "scopes": ["course:read", "course:write", "course:reset"]
}
```

Only `demo` and `course` environments are accepted. Reset requires `demo`. A course token is not a production Social token. No token, password, cookie or SQL error belongs in a response artifact.

## Records, revisions and readback

- `GET /records/{collection}/{id}` returns one canonical record.
- `GET /records/{collection}?limit=20` returns `{ "items": [...] }`, most recently updated first, capped at 500. These are recent records, not an exhaustive dataset export; domain operations resolve deterministic ids rather than using a truncated list for uniqueness.
- `PUT /records/{collection}/{id}` atomically creates or updates the record. Body: `{ "schema_version": 1, "expected_revision": 0, "data": { ... } }`.
- On create, `expected_revision` is 0; each successful write increments it by exactly one. Updates require the current revision; otherwise return 409/412. Canonical readback uses a separate GET and must match content and revision exactly.
- The client sends `Idempotency-Key = SHA256(canonical_json([method, relative_path, body]))`. Bind replay to token principal, organization, workspace and key. Identical replay after an uncertain acknowledgement returns the original revision, never another mutation. A key with different content must be rejected.

Canonical record envelope:

```json
{
  "organization_id": "demo-org", "workspace_id": "student-01",
  "actor_id": "authenticated-user-id", "collection": "knowledge_notes",
  "id": "weekly-note", "revision": 1,
  "created_at": "2026-08-30T12:00:00+00:00",
  "updated_at": "2026-08-30T12:00:00+00:00",
  "data": { "summary": "A reviewed, cited note" }
}
```

The server assigns actor and timestamps. Validate every field and domain schema before writing; never spread arbitrary client objects into DB entities. Enforce a 512,000-byte JSON bound, content limits and per-principal rate limits. The client rejects obvious credential fields and home paths; that check is not comprehensive data-loss prevention. Raw source files, code repositories, screenshots and binaries stay local/by-reference by default. Do not parse Markdown or input documents as executable instructions.

## Execution/provenance layer

`skill_runs` records contain `schema_version`, `skill_name`, `run_id`, `status`, `created_at`, `updated_at`, optional `finished_at`, `input_summary`, `metadata`, `events`, `artifacts`, and `source_refs`. Status is `running`, `previewed`, `awaiting_approval`, `succeeded`, `failed` or `partial`.

Events contain `id`, `run_id`, `event_type`, `payload`, `created_at`. Artifacts contain `id`, `run_id`, `artifact_type`, `title`, `content_json`, `source_ref`, `created_at`. Source references use a stable `id`, `source_type`, relative `source_ref`, hashes and source modification time where available. The backend may normalize the envelope into `skill_runs`, `skill_events`, `skill_artifacts` and `skill_source_refs` in one transaction; it must reconstruct an equivalent canonical envelope for readback. Identity/tenancy columns belong to every normalized row, not only the parent run.

## Domain collections

The allowlist in `course_runtime.py` is the client contract:

- Lesson 2: `knowledge_sources`, `knowledge_notes`, `workflow_definitions`; workflow runs/steps are execution records/events.
- Lesson 3: `web_projects`, `web_test_runs`, `deployment_records`; source code remains in Git, screenshot binaries remain local.
- Lesson 4: `business_datasets`, `crm_contacts`, `crm_deals`, `crm_activities`, `crm_tasks`, `analysis_runs`; synthetic course data only, deterministic entity keys, referential integrity and compare-and-swap updates.
- Lesson 5: `content_strategies`, `aeo_audits`; **no generic social campaign/post/schedule collections**. Social IDs reference the existing canonical Social API/model.

These collections may become domain tables under the owning app's existing Neon connection. The owner must decide migration/schema placement; this document does not authorize a second identity system or a new production database.

## Demo reset

`GET /reset-preview` returns scoped counts. `POST /reset` requires `course:reset`, `environment=demo` and `{ "confirmation": "exact-workspace-id" }`. Acknowledge `organization_id`, `workspace_id` and deleted-record counts. Invalidate only demo course records, verify all course collections are empty, and never reset canonical Social records or real business objects. Respect active-run locks so reset cannot erase a run that is still executing.

## Error and retry contract

Use 401 for missing/expired token, 403 for denied scope, 404 for unknown resource, 409/412 for revision conflict, 422 for invalid data, 429 with Retry-After for rate limits and 5xx for unavailable dependencies. Missing `/context` maps to `BACKEND_NOT_READY`. The client never automatically retries a mutation and never falls back to SQLite in remote mode. It reports `READBACK_MISMATCH` when the write may have succeeded but cannot be verified; inspect the canonical id before retrying the same payload. Never store or echo raw API error bodies.

A local action may complete before its final remote update fails. Organizer intent/action journals and workflow step journals are saved locally before/after effects. Stop subsequent steps; reconcile or undo locally. An interrupted non-idempotent workflow step requires human inspection, not automatic replay.

## Owner acceptance tests

The backend stream must prove expired/revoked tokens, cross-tenant read/write/list/reset, actor spoofing, stale updates, same-key retries, same-key different-body rejection, invalid domain payloads, rate limits, active-run reset prevention and read-after-write persistence across server restarts. Run migrations against a disposable Neon branch, then verify instructor-provisioned course access in the real deployed UI/API. Client mocks alone cannot satisfy this gate.
