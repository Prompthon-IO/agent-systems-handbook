# Persistence contract

`web_test_runs` stores suite, project id, source fingerprint, viewport checks, failed step, console error hashes/counts and screenshot file references/hashes. PNG binaries and raw console strings stay out of the API. `skill_runs` records final state. Evidence files live below the current workspace's `web-evidence/<test_id>` directory.

Use shared `Store` and `Run`; do not create a parallel database or direct database driver. Every record is tenant/workspace/actor scoped, updates use revision checks, and successful writes require canonical readback. See [schema, auth, errors and reset](../../course-support/references/backend-contract.md). Source files remain local/Git. The course API is an explicit backend dependency, not a claimed live service.
