# Persistence contract

`web_projects` stores the approved brief, file names/hashes, source fingerprint, build check, last run and explicit `ui_qa: not_run`. `skill_runs` stores actions and evidence references. Existing-stack `record` preserves source only in Git; do not upload source or command output.

Use shared `Store` and `Run`; do not create a parallel database or direct database driver. Every record is tenant/workspace/actor scoped, updates use revision checks, and successful writes require canonical readback. See [schema, auth, errors and reset](../../course-support/references/backend-contract.md). Source files remain local/Git. The course API is an explicit backend dependency, not a claimed live service.
