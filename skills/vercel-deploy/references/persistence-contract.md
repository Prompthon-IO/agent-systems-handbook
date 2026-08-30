# Persistence contract

`deployment_records` stores provider deployment id, URL, project id, commit SHA, target, ready state, matching test/source fingerprint and URL-readback result. `skill_runs` records submission/verification state. Local `deployment-attempts/<attempt>.json` survives an API failure. No token, full provider response, source bundle or raw command log is stored. A failed metadata write does not undo an external deployment.

Use shared `Store` and `Run`; do not create a parallel database or direct database driver. Every record is tenant/workspace/actor scoped, updates use revision checks, and successful writes require canonical readback. See [schema, auth, errors and reset](../../course-support/references/backend-contract.md). Source files remain local/Git. The course API is an explicit backend dependency, not a claimed live service.
