# Persistence contract

Social business objects remain in the existing `social_campaign`, `social_post_draft`, variant/schedule/publish-target/delivery and audit models. Course prep stores only `skill_runs` and a local plan; there are no new social course tables. Campaign/post metadata links strategy id/revision and course workspace. The proposed server receipt reconciler validates existing Host receipts and writes common skill-run evidence; no caller-supplied success file is trusted as live proof.

Common course records use the [shared scoped API contract](../../course-support/references/backend-contract.md). The owning Web App must provision auth, tenant isolation and schema before remote use. Social remains on its current canonical domain; do not create parallel social tables to imitate scheduling.
