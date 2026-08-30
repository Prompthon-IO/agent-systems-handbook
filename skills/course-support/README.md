# Adult course skill support

This is shared infrastructure, not a thirteenth skill. Tier 1 Lessons 2–5 teach twelve separate jobs. The canonical packages remain under `skills/`; generated Codex copies go under `.agents/skills/`.

| Lesson | Capabilities | Packages |
| --- | --- | --- |
| 2 | Organize → Understand → Automate | local-document-organizer, personal-knowledge-capture, personal-workflow-automation |
| 3 | Build → Test → Deploy | web-builder, webapp-testing, vercel-deploy |
| 4 | Structure → Operate → Analyze | business-data-structuring, crm-operations, business-data-analysis |
| 5 | Plan → Distribute → Discover | content-strategy, prompthon-social-campaign-manager, ai-search-visibility |

The installer discovers the `course.json` files actually present in your checkout. A lesson is ready only when all three packages and its lab exist; a name in this curriculum map is not deployment evidence.

## Prerequisites and five-minute setup

Use Python 3.10+ and Git. Fork the handbook, clone your fork, and open that clone in Codex. Run commands from the repository root. The core helpers use the Python standard library; optional PDF, XLSX and browser dependencies are documented by their packages. No OpenAI API key or production database password is required for local exercises.

```bash
python3 skills/course-support/scripts/setup_course_skills.py --lesson 2 --dry-run
python3 skills/course-support/scripts/setup_course_skills.py --lesson 2
python3 skills/course-support/scripts/setup_course_skills.py --lesson 2 --check
python3 skills/course-support/scripts/seed_demo.py
python3 skills/course-support/scripts/course_store.py context
```

Mention `$local-document-organizer` in Codex. Reload/restart Codex if its skill list has not refreshed. The installer copies files on Windows, macOS and Linux; it does not require symlink permissions. It refuses to overwrite unmanaged packages or edited installed copies. Edit canonical `skills/<name>/` files, then rerun setup; `--replace` explicitly discards edits to generated copies only.

Local exercises use organization `demo-org`, workspace `demo-student`, and actor `demo-student`. Set `--organization`, `--workspace` and `--state-dir` **before** the subcommand to keep students separate on a shared machine. Local identity is a classroom label, not authentication. Runtime files stay in ignored `.local-state/`, never in fixtures or a student's commit.

## Classroom mode and the backend dependency

The course standard is `--storage prompthon`: local Codex execution with canonical state behind a Prompthon-owned API and Neon/PostgreSQL. The API contract and its production deployment are separate deliverables. **This repository does not supply or claim a deployed course API, production sign-in, token issuer, database schema migration or Neon environment.** The backend owner must complete [the dependency handoff](references/backend-dependency.md) before instructors enable remote mode.

Once provisioned, supply the owner-confirmed HTTPS origin, organization, workspace and a short-lived scoped token through environment variables (or a token file). The client reads `PROMPTHON_COURSE_API_URL`, `PROMPTHON_COURSE_ORGANIZATION`, `PROMPTHON_COURSE_WORKSPACE` and `PROMPTHON_COURSE_TOKEN_FILE` / `PROMPTHON_COURSE_TOKEN`. Do not paste tokens in commands, screenshots, fixtures, artifacts or git. There is deliberately no default production origin.

```bash
python3 skills/course-support/scripts/course_store.py --storage prompthon context
python3 skills/course-support/scripts/course_store.py --storage prompthon runs
```

The backend must resolve the actor from its existing authenticated user and attest the exact demo/course organization and workspace. The client refuses production contexts, redirects, missing permissions, stale revisions and mismatched readback. Remote failures remain failures; there is no silent local fallback. `--allow-loopback` is only for a deliberately selected local contract-test server, not an authentication bypass.

Read [the contract](references/backend-contract.md) for endpoint shapes, scopes, error codes, idempotency and domain ownership. The original Social Media Manager canonical campaign/post model remains owned by the Social service, never by generic course tables.

## Teaching and modification

Start with [Lesson 2](lessons/lesson-2.md) and its [Simplified Chinese version](zh-Hans/lesson-2.md). Later lesson labs live beside them when installed in this checkout. Every package README provides a five-minute exercise, sample Codex prompt, a 20–30 minute extension, expected output, persistence readback, reset and approval points.

Modify one classification rule, source, workflow gate, data field, test assertion or content criterion at a time. Preview the effect, run the helper, compare the persisted result, and commit only the canonical source change to your fork. The deterministic outputs are evidence and starting drafts; use Codex for judgment, cited synthesis and context-specific design.

Course helpers use exit 0 for a completed request (including an explicit preview), 1 for failed/partial execution, 2 for refused or invalid operations, and 3 for an approval pause. Inspect the JSON status and readback evidence as well.

## Reset and recovery

```bash
python3 skills/course-support/scripts/course_store.py reset
python3 skills/course-support/scripts/course_store.py reset --confirm demo-student
```

Reset previews the current workspace's course rows, then requires its exact workspace id. Remote reset additionally requires `course:reset` and a server-attested `demo` environment. It never deletes original local files, undo journals, other workspaces, real CRM data or canonical Social records. Use the organizer's undo command before resetting its run metadata. To restart fixtures, seed a **new** output directory; never erase an arbitrary Downloads or Documents folder.

## Validation

```bash
python3 skills/course-support/scripts/verify_course_skills.py
python3 scripts/verify_example_projects.py
python3 scripts/check_filename_casing.py
python3 scripts/check_published_links.py
```

Course verification runs meaningful local and HTTP contract tests, including tenant mismatch, stale writes, readback differences, fail-closed remote errors, no-overwrite moves, undo, source deduplication and workflow approval gates. These tests are not a live Neon or Vercel deployment check. Instructors must separately verify provisioned remote persistence and deployment URLs before claiming the remote classroom is ready.

## Sources

Read the pinned [source audit](references/source-audit.json) and each package's source notes. The helpers and course instructions are original adaptations; no external Skill prose or code is vendored. Restricted or unverified upstream licenses are not treated as permission to copy.

Codex discovery and package metadata follow the [official Skills documentation](https://developers.openai.com/codex/skills), reviewed 2026-08-30. English is canonical; Chinese labs mirror the same requirements and limits.
