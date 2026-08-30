# Persistence contract

`analysis_runs` stores the six report sections, schema/quality aggregates, source reference/hash or dataset id/revision, calculation description and report digest. `skill_runs` records execution. The helper never writes source CSV/XLSX/JSON or CRM objects; reports are new local files plus canonical analysis records. Remote metadata-only dataset records cannot be analyzed as if rows were available.

Use shared Store/Run, never a parallel persistence client. Tenant/workspace/actor, revision CAS, idempotency, error handling and reset follow the [shared API contract](../../course-support/references/backend-contract.md). Production API/migrations/auth are implemented by the owning Web App stream, not assumed to exist because these local fixtures pass.
