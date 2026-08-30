# Course persistence

Use the shared client in `skills/course-support/scripts/course_runtime.py`.
The versioned [backend contract](../../course-support/references/backend-contract.md) defines local versus Prompthon storage, scope, errors, revisions and mandatory readback.

This package has no production database credentials. New course endpoints remain an explicit Web App dependency; a local contract test is not evidence of a Neon deployment.
