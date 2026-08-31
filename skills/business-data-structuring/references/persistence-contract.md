# Persistence contract

`business_datasets` holds schema, grain, source hash, shape, null/duplicate/error inspection, plan hash and local output references/hashes. Local mode also stores normalized rows; remote row sharing is explicit. `skill_runs` records the operation. Output is written before registration so a failed remote write leaves recoverable local evidence; it is not a successful remote save.

Use shared Store/Run, never a parallel persistence client. Tenant/workspace/actor, revision CAS, idempotency, error handling and reset follow the [shared API contract](../../course-support/references/backend-contract.md). Production API/migrations/auth are implemented by the owning Web App stream, not assumed to exist because these local fixtures pass.
