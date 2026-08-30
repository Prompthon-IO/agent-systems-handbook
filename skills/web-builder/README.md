# Web Builder

Lesson 3 · **Build** · `$web-builder`

Inspect an existing web project and create or modify a working local page from a purpose, audience, sections, style and constraints brief. Use for building a website; leave final browser QA to webapp-testing and publishing to vercel-deploy.

## Prerequisites

Requires the course foundation (PR #222), Python 3.10+, and the sibling Lesson 3 packages. Build needs Node.js; Test needs the pinned Playwright/Chromium environment; actual Deploy needs instructor-provisioned Vercel access. Run commands from the handbook root. On Windows, use `python` or `py` instead of `python3` as appropriate.

## Five-minute quickstart

```bash
python3 skills/course-support/scripts/setup_course_skills.py --lesson 3
python3 skills/web-builder/scripts/web_builder.py --dry-run build --project .local-state/course-site --brief skills/web-builder/examples/workshop-brief.json
python3 skills/web-builder/scripts/web_builder.py build --project .local-state/course-site --brief skills/web-builder/examples/workshop-brief.json --confirm BUILD
```

Expected: three local files, a successful `node --check app.js`, a `web_projects` record and `skill_runs` entry, and `ui_qa: not_run`. Open `index.html` locally or pass the project to Test. The form only displays a demo message; it sends no email and saves no signup.

## 20–30 minute exercise and one modification

Spend 5 minutes reviewing the brief, 10 minutes changing audience and one section in a copied brief, 5 minutes building, and 5 minutes comparing the page against the request. Change `style_direction` to `bold-contrast` and use a new output directory. For an existing React/Next app, inspect and use its existing scripts instead of this scaffold.

## Read back the saved result

Use the same `--storage`, organization, workspace and state directory as the original run. Replace uppercase IDs with the actual returned value:

```bash
python3 skills/course-support/scripts/course_store.py read web_projects course-site
python3 skills/course-support/scripts/course_store.py runs --skill web-builder
```

## Persistence, reset and recovery

`web_projects` stores the approved brief, file names/hashes, source fingerprint, build check, last run and explicit `ui_qa: not_run`. `skill_runs` stores actions and evidence references. Existing-stack `record` preserves source only in Git; do not upload source or command output.

Global options precede a subcommand. All helpers accept `--storage local|prompthon`, `--organization`, `--workspace`, `--state-dir` and `--dry-run`. Remote mode is **not deployed by this package**; follow [shared setup](../course-support/README.md) and [backend dependency](../course-support/references/backend-dependency.md). A remote failure never silently switches to local success.

Preview reset with `python3 skills/course-support/scripts/course_store.py reset`; after reviewing its scope, add `--confirm demo-student` for the current demo workspace. Reset removes course records across lessons, not source projects, screenshots or provider deployments. Keep those for recovery or select a fresh workspace and output folder; do not run a broad delete command.

## Instructor notes and validation

Use synthetic fixtures and separate student workspaces. Preinstall dependencies and inspect every learner's actual output rather than trusting an agent's success sentence. Keep Build, Test and Deploy as separate responsibilities. The [English lab](../course-support/lessons/lesson-3.md) and [中文课堂指引](../course-support/zh-Hans/lesson-3.md) connect them.

Run the web lifecycle tests with the Playwright venv. They exercise the browser and deployment safety/readback contracts; provider responses in those unit tests are mocks, not evidence of a live Vercel deployment.

See [safety rules](references/safety-rules.md), [persistence contract](references/persistence-contract.md), and [source notes](references/source-notes.md).
