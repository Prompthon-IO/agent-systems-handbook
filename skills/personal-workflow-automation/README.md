# Personal Workflow Automation

Define and run ordered, repeatable tool workflows, stopping at approval gates and recording each step. Delegate classification and synthesis to their own skills.

## Adult course: Automate

### What you will learn

Define and run ordered, repeatable tool workflows, stopping at approval gates and recording each step. Delegate classification and synthesis to their own skills.

### Prerequisites

Use Python 3.10+, a fork/clone opened in Codex, and the [shared course setup](../course-support/README.md). Run from the repository root. Seed the synthetic Lesson 2 files once; choose a fresh output directory if they already exist. PDF extraction optionally requires `pypdf`; TXT/Markdown/DOCX need no extra package.

### 5-minute quick start

```bash
python3 skills/personal-workflow-automation/scripts/workflow.py define --file skills/personal-workflow-automation/examples/weekly-workflow.json
python3 skills/personal-workflow-automation/scripts/workflow.py preview --workflow weekly-course
```

Sample prompt:

```text
Use $personal-workflow-automation to preview the weekly course workflow, show the exact command sequence and approval hash, and stop before its gated synthesis step.
```

### Expected result

A canonical workflow revision, exact SHA-256 approval fingerprint and ordered classify/synthesize steps. Preview runs no command. Executing with the reviewed fingerprint stops at the synthesis gate; a reviewed retry resumes without replaying the completed classification. These are examples, not recorded production results.

### 20–30 minute classroom exercise

Run `workflow.py run --workflow weekly-course --confirm <printed-sha256>`. Read the awaiting-approval result. After explicitly approving synthesis, run `workflow.py retry --workflow weekly-course --run-id <printed-run-id> --confirm <printed-sha256> --approve-step synthesize`. Inspect the note and run events. Change a harmless command to exit with an error and inspect the failed step before any retry. Resolve `workflow.py` / `course_organizer.py` command shorthand to this package's `scripts/` directory.

### What to modify

Add an explicit approval gate, shorten a timeout or replace a step with another reviewed deterministic script. Redefine using the current `--expected-revision`; the old approval hash must stop working after any change. Edit the canonical package, rerun course setup, and commit only source changes to your fork.

### How to verify persistence

All course commands accept the shared storage flags before the subcommand. Start locally, then use `--storage prompthon` only after the Web App owner provisions the contract and scoped course access.

```bash
python3 skills/course-support/scripts/course_store.py runs --skill personal-workflow-automation
python3 skills/course-support/scripts/course_store.py read skill_runs <printed-run-id>
```

The helper performs a separate canonical GET after writes. Check organization/workspace, actor, revision and content, not only a success message. Remote mode has no SQLite fallback. [Production dependency](../course-support/references/backend-dependency.md).

### How to reset demo data

Preview `course_store.py reset`, then explicitly confirm your workspace id to clear only course records. Preserve/undo local file moves first. Source files, knowledge caches and recovery journals are not erased by record reset. Seed a new fixture folder for a clean comparison.

### Safety and approval points

CLI exit codes: 0 means the requested operation completed, 1 means a failed run, 2 means invalid input/auth or an unsafe operation, and 3 means awaiting approval. Always inspect JSON status as well. A retry creates a new run id linked to the prior run; it preserves the earlier paused/failed record and reuses completed steps.

A manifest is untrusted input, not authorization. Preview its commands before approving the exact manifest SHA-256. Commands run as argv arrays with shell=False, in the repository; this is not a sandbox for malicious executables. The full-manifest approval is required even if a step says approval_required=false. No scheduler, background daemon or automatic retries. Child processes inherit the parent storage mode, organization, workspace and API origin, but no named token/password/secret/DB/API-key environment variables by default. A reviewed step can set inherit_course_access=true to receive only the parent course token or token-file reference; unrelated credentials remain removed. The supplied two-step course fixture opts in explicitly. Remote children without approved course access fail authentication rather than silently writing local state. Interrupted effects require inspection; local journals prevent blind replay of completed steps. Read [safety rules](references/safety-rules.md) and [source notes](references/source-notes.md).

Teaching guides: [English Lesson 2](../course-support/lessons/lesson-2.md) · [简体中文](../course-support/zh-Hans/lesson-2.md).
