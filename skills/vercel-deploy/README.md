# Vercel Deploy

Lesson 3 · **Deploy** · `$vercel-deploy`

Deploy an approved and tested committed web project to a Vercel preview and verify provider identity, commit, status and actual URL. Use for publishing a website preview; production needs separate approval, and feature building or browser QA belong to other skills.

## Prerequisites

Requires the course foundation (PR #222), Python 3.10+, and the sibling Lesson 3 packages. Build needs Node.js; Test needs the pinned Playwright/Chromium environment; actual Deploy needs instructor-provisioned Vercel access. Run commands from the handbook root. On Windows, use `python` or `py` instead of `python3` as appropriate.

## Five-minute quickstart

With no Vercel credentials, run the local contract checks below and inspect `examples/readback-cases.json`; these are synthetic tests and produce **no real preview URL**.

```bash
.local-state/course-venv/bin/python -m unittest discover -s skills/web-builder/tests -p 'test_*.py' -v
```

For a real preview, the instructor supplies an existing Git-linked Vercel demo project, a reviewed commit, matching build/test records and its actual deployment id. Set `VERCEL_ACCESS_TOKEN` privately or use a protected `--vercel-token-file`; never paste the credential into a prompt. Substitute the angle-bracket values (they are placeholders, not runnable sample IDs):

```text
python3 skills/vercel-deploy/scripts/course_deploy.py verify --project <project-path> --project-id course-site --test-id <passing-test-id> --expected-commit <full-commit-sha> --deployment <actual-deployment-id> --vercel-project <actual-project-id> --expected-text "Build your first useful AI website"
```

Expected: either an actual provider-verified preview URL and commit, or an explicit unverified/failed result. Never report the fixture's synthetic domain as deployed. Read `references/provider-workflow.md` for the approved CLI fallback.

## 20–30 minute exercise and one modification

With preprovisioned course access, spend 5 minutes checking project/commit/test identity, 10 minutes creating an approved Git preview, 5 minutes reading back READY and the page marker, and 5 minutes comparing the stored deployment record to Vercel. Modify a heading, rebuild, commit and retest before the next preview. Without provider access, use the synthetic cases and report the deployment prerequisite as unresolved; do not claim a live lesson outcome.

## Persistence, reset and recovery

`deployment_records` stores provider deployment id, URL, project id, commit SHA, target, ready state, matching test/source fingerprint and URL-readback result. `skill_runs` records submission/verification state. Local `deployment-attempts/<attempt>.json` survives an API failure. No token, full provider response, source bundle or raw command log is stored. A failed metadata write does not undo an external deployment.

Global options precede a subcommand. All helpers accept `--storage local|prompthon`, `--organization`, `--workspace`, `--state-dir` and `--dry-run`. Remote mode is **not deployed by this package**; follow [shared setup](../course-support/README.md) and [backend dependency](../course-support/references/backend-dependency.md). A remote failure never silently switches to local success.

Preview reset with `python3 skills/course-support/scripts/course_store.py reset`; after reviewing its scope, add `--confirm demo-student` for the current demo workspace. Reset removes course records across lessons, not source projects, screenshots or provider deployments. Keep those for recovery or select a fresh workspace and output folder; do not run a broad delete command.

## Instructor notes and validation

Use synthetic fixtures and separate student workspaces. Preinstall dependencies and inspect every learner's actual output rather than trusting an agent's success sentence. Keep Build, Test and Deploy as separate responsibilities. The [English lab](../course-support/lessons/lesson-3.md) and [中文课堂指引](../course-support/zh-Hans/lesson-3.md) connect them.

Run the web lifecycle tests with the Playwright venv. They exercise the browser and deployment safety/readback contracts; provider responses in those unit tests are mocks, not evidence of a live Vercel deployment.

See [safety rules](references/safety-rules.md), [persistence contract](references/persistence-contract.md), and [source notes](references/source-notes.md).
