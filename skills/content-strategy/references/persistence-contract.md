# Persistence contract

`content_strategies` stores the brief, pillars, clusters, ranked topics, evidence references, editorial scores and calendar under a stable strategy id with revision CAS. Each save has a `skill_runs` entry and a local revision snapshot. A subsequent campaign records the strategy id/revision in the existing Social campaign metadata.

Common course records use the [shared scoped API contract](../../course-support/references/backend-contract.md). The owning Web App must provision auth, tenant isolation and schema before remote use. Social remains on its current canonical domain; do not create parallel social tables to imitate scheduling.
