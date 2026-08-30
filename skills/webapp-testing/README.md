# Web App Testing

Lesson 3 · **Test** · `$webapp-testing`

Verify a local web app in a real browser with page, element, click, form, console and screenshot evidence. Use after a build or UI change; do not implement features or publish deployments with this skill.

## Prerequisites

Requires the course foundation (PR #222), Python 3.10+, and the sibling Lesson 3 packages. Build needs Node.js; Test needs the pinned Playwright/Chromium environment; actual Deploy needs instructor-provisioned Vercel access. Run commands from the handbook root. On Windows, use `python` or `py` instead of `python3` as appropriate.

## Five-minute quickstart

First build the fixture using [Web Builder](../web-builder/README.md). Install dependencies once:

```bash
python3 -m venv .local-state/course-venv
.local-state/course-venv/bin/python -m pip install -r skills/webapp-testing/requirements.txt
.local-state/course-venv/bin/python -m playwright install chromium
.local-state/course-venv/bin/python skills/webapp-testing/scripts/webapp_test.py --project .local-state/course-site --suite skills/webapp-testing/examples/workshop-suite.json
```

Windows: use `.local-state/course-venv/Scripts/python.exe` in place of the venv interpreter. The first dependency/browser download can take longer than five minutes; instructors should preinstall it.

Expected: `status: passed`, two viewport results, 0 console errors, 0 blocked requests, a `test_id` and local `evidence_dir` containing two PNGs. Open those PNGs; remote records contain only relative references/hashes. Exit 1 means test failure; exit 2 means setup/refusal, never a pass.

## 20–30 minute exercise and one modification

Spend 5 minutes reading the suite, 10 minutes adding a heading assertion and checking both screenshots, 5 minutes intentionally changing the expected heading to see a failing step, and 5 minutes fixing it and comparing two persisted runs. Optional: introduce a synthetic console.error, observe a failure, remove it and rerun.

## Persistence, reset and recovery

`web_test_runs` stores suite, project id, source fingerprint, viewport checks, failed step, console error hashes/counts and screenshot file references/hashes. PNG binaries and raw console strings stay out of the API. `skill_runs` records final state. Evidence files live below the current workspace's `web-evidence/<test_id>` directory.

Global options precede a subcommand. All helpers accept `--storage local|prompthon`, `--organization`, `--workspace`, `--state-dir` and `--dry-run`. Remote mode is **not deployed by this package**; follow [shared setup](../course-support/README.md) and [backend dependency](../course-support/references/backend-dependency.md). A remote failure never silently switches to local success.

Preview reset with `python3 skills/course-support/scripts/course_store.py reset`; after reviewing its scope, add `--confirm demo-student` for the current demo workspace. Reset removes course records across lessons, not source projects, screenshots or provider deployments. Keep those for recovery or select a fresh workspace and output folder; do not run a broad delete command.

## Instructor notes and validation

Use synthetic fixtures and separate student workspaces. Preinstall dependencies and inspect every learner's actual output rather than trusting an agent's success sentence. Keep Build, Test and Deploy as separate responsibilities. The [English lab](../course-support/lessons/lesson-3.md) and [中文课堂指引](../course-support/zh-Hans/lesson-3.md) connect them.

Run the web lifecycle tests with the Playwright venv. They exercise the browser and deployment safety/readback contracts; provider responses in those unit tests are mocks, not evidence of a live Vercel deployment.

See [safety rules](references/safety-rules.md), [persistence contract](references/persistence-contract.md), and [source notes](references/source-notes.md).
