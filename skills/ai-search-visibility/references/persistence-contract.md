# Persistence contract

`aeo_audits` stores target queries, scope hash, page source hashes/URLs, structural signals, short evidence excerpts, findings, recommendations and recheck comparison under a stable audit id/revision. `skill_runs` records each audit. Local snapshots are never uploaded as raw HTML, and the audit does not modify them. New reports are saved separately.

Common course records use the [shared scoped API contract](../../course-support/references/backend-contract.md). The owning Web App must provision auth, tenant isolation and schema before remote use. Social remains on its current canonical domain; do not create parallel social tables to imitate scheduling.
