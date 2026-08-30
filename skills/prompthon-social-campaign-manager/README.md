# Prompthon Social Campaign Manager

Lesson 5 · **Distribute** · `$prompthon-social-campaign-manager`

Prepare channel-specific Prompthon social campaigns from a saved strategy and use guarded canonical Social operations when an isolated demo workspace is available. Use for course distribution drafts or explicitly requested production operation; keep strategy design separate and verify the deployed auth contract before any legacy production flow.

## Prerequisites and five-minute quickstart

Requires the course foundation (#222), Lesson 5 packages and Python 3.10+. Commands run from the handbook root; Windows users may substitute `python`/`py` for `python3`. Use synthetic fixtures and an isolated student workspace. Social browser-adapter contract tests also need Node.js; actual browser execution needs separately provisioned demo backend capability and a signed-in Host session.

First save the strategy using [Plan](../content-strategy/README.md), then run:

```bash
python3 skills/prompthon-social-campaign-manager/scripts/course_social.py --request skills/prompthon-social-campaign-manager/examples/course-campaign.json
python3 skills/course-support/scripts/course_store.py runs --skill prompthon-social-campaign-manager
```

Expected: `status: prepared`, two parent-post previews with distinct LinkedIn/Facebook copy, a plan file/hash and `canonical_social_objects_created: false`. Open the returned JSON file. No real channel is connected or contacted, and the canonical Social tables are untouched.

Sample Codex prompt:

> Use $prompthon-social-campaign-manager in course mode with my saved workshop strategy and the example campaign request. Prepare LinkedIn and Facebook variants, show the strategy revision and plan hash, and read back the preview run. Stop at preparation; do not create a real campaign, schedule, connect a channel or publish anything.

The backend's isolated-demo attestation, simulation worker policy and receipt reconciliation are **pending dependency #221**. Until provisioned and live verified, do not promise a real demo schedule/status. The offline contract harness can be run with `node skills/prompthon-social-campaign-manager/tests/test_course_browser.cjs PLAN_FILE` after preparing a test plan with explicit `--api-url https://course.example.invalid`; all fetches there are intercepted and no provider is contacted.

## 20–30 minute exercise and one modification

Spend 5 minutes choosing strategy topics, 10 minutes adapting the core message into two channel voices, 5 minutes generating/inspecting the plan, and 5 minutes checking strategy linkage and no-send state. Modification: change one provider copy and observe a new plan hash. With separately provisioned demo access, practice DRAFT then additional SCHEDULE approval and actual canonical readback; without it, use the clearly synthetic contract harness and mark live demo scheduling unresolved.

## Persistence, readback and recovery

Social business objects remain in the existing `social_campaign`, `social_post_draft`, variant/schedule/publish-target/delivery and audit models. Course prep stores only `skill_runs` and a local plan; there are no new social course tables. Campaign/post metadata links strategy id/revision and course workspace. The proposed server receipt reconciler validates existing Host receipts and writes common skill-run evidence; no caller-supplied success file is trusted as live proof.

Select global `--storage local|prompthon`, organization, workspace and state directory before subcommands; use the same scope for readback. The default is local/offline. Remote API/auth/Neon deployment is not created by installing these packages. A failed remote write does not silently become local success. See [shared setup](../course-support/README.md).

Read runs with `python3 skills/course-support/scripts/course_store.py runs --skill prompthon-social-campaign-manager`. Every reported id must come from the actual tool response; fixture domains and mock receipts are not live results.

## Reset and instructor notes

Preview the shared `course_store.py reset`, review its scope, then confirm the selected demo workspace with `--confirm demo-student`. It removes all course records in that workspace, not files, web pages, canonical Social campaigns/posts or external deliveries. Use a fresh workspace for repeat exercises and the owning app's separately authorized cleanup flow for actual Social objects; never silently delete them.

Review the actual source, plan, canonical records and audit/report evidence. A content calendar is not a schedule; a course simulation is not public publication; an AEO heuristic is not measured ranking. [English lab](../course-support/lessons/lesson-5.md) · [中文课堂指引](../course-support/zh-Hans/lesson-5.md).

Validate with `python3 -m unittest discover -s skills/content-strategy/tests -p 'test_*.py' -v`. This includes an entirely mocked Node Social contract harness; no external delivery is performed. See [safety](references/safety-rules.md), [persistence](references/persistence-contract.md), and [sources](references/source-notes.md).

The original production helper is preserved unchanged. Historical [production guide](references/production-guide.md), [production workflow](references/production-workflow.md), [API reference](references/api-contract.md), and [bridge reference](references/browser-bridge-contract.md) remain available, but current auth/transport must be verified before use. Read the [canonical Host contract](references/canonical-host-contract.md) and [course backend dependency](references/course-backend-dependency.md) before any browser execution.
