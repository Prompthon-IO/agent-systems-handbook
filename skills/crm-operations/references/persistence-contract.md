# Persistence contract

Use existing course collections `crm_contacts`, `crm_deals`, `crm_activities`, `crm_tasks` plus `skill_runs`. Each entity includes an atomic audit list with actor, time, run id, before/after and approval hash. Canonical scope/revision/readback comes from the shared Store. No third-party CRM table or separate SQLite database is introduced.

Use shared Store/Run, never a parallel persistence client. Tenant/workspace/actor, revision CAS, idempotency, error handling and reset follow the [shared API contract](../../course-support/references/backend-contract.md). Production API/migrations/auth are implemented by the owning Web App stream, not assumed to exist because these local fixtures pass.
