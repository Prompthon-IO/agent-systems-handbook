# Local Document Organizer

## Why This Skill Exists

This package is a Practitioner-facing example of a safety-sensitive local
filesystem workflow.

"Organize my Downloads" sounds trivial, but as soon as the agent starts
moving files, it becomes one of the easier ways to lose work: a wrong
classification, a silent overwrite, or a missing undo path can turn a
helpful action into a recovery problem. The package shows how a Codex skill
can do the useful thing while keeping the user in control.

The pattern is intentionally cautious:

- preview before any move
- explicit confirmation token, not inferred consent
- never delete, never overwrite
- low-confidence files default to staying put
- every applied move is logged with enough information to reverse it

## Who It Is For

This skill is for students, contributors, and operators who want to see what
a real Codex-compatible local workflow looks like when filesystem safety
matters and the user expects to be able to undo an action they did not love.

It is most useful for requests such as:

- propose a folder structure for a messy Downloads folder
- sort invoices, receipts, tax forms, and school documents into named
  subfolders
- preview what would happen before any file is touched
- reverse a previous organization run

## End-to-End Workflow

The workflow is split into three commands so each phase has a clear
boundary:

1. **Scan.** The user names a folder. The skill walks it, classifies each
   file using the rules in `references/classification-rules.csv`, and writes
   a Markdown report plus a JSON plan. No files are moved.
2. **Apply.** After the user reviews the preview and explicitly approves,
   the skill runs `apply --confirm ORGANIZE` against the plan. It creates
   category subfolders, moves files, and writes an action log. Conflicts
   and permission errors are recorded as skipped actions.
3. **Undo.** If the user wants to revert the run, the skill reads the
   action log and moves each file back to its original path.

The agent surfaces the report, the plan, the action log path, and the
results. The user owns the decision to apply and the decision to undo.

## What The Package Actually Does

- Reads classification rules from a small CSV (extension and filename
  keyword matches with confidence scores).
- Walks the user-named folder, classifies each file in CSV order with
  first-match-wins semantics, and produces a deterministic plan.
- Writes a Markdown preview that groups proposed moves by category and
  surfaces skipped or low-confidence files.
- Executes only the moves the user has approved with the `ORGANIZE` confirm
  token.
- Persists run state in
  `~/.codex/state/local-document-organizer/organizer.sqlite` so past runs
  remain inspectable across sessions.
- Provides an undo command that reverses recorded moves without overwriting.

## What It Does Not Do

This package does not:

- delete files (no `unlink`, no `rmtree`)
- overwrite files (destination collisions are skipped)
- act on `/`, `/System`, `/Library`, `~/Library`, `~/.ssh`, `~/.gnupg`,
  `~/.aws`, or the home directory itself
- move low-confidence or unmatched files unless the user explicitly opts in
  with `--include-low-confidence`
- send any data to external services

## How To Read It In The Handbook

Treat this package as a Practitioner example of a destructive-looking
workflow that stays reversible:

- `README.md` explains the human story and the three-phase boundary
- `SKILL.md` is the invocation contract for Codex
- `scripts/local_document_organizer.py` implements the deterministic helper
- `references/classification-rules.csv` holds the readable category rules
- `references/safety-rules.md` documents the hard prohibitions and skip
  semantics

If you are a student reading the repo, the main lessons are:

1. preview-first is not a courtesy, it is a safety property
2. an explicit confirmation token (`ORGANIZE`) is harder to grant by
   accident than a free-form "yes"
3. an action log is the difference between a regret and a recovery

## Adult course: Organize

### What you will learn

Classify and safely relocate local files, with preview, approval and undo. Do not synthesize their knowledge.

### Prerequisites

Use Python 3.10+, a fork/clone opened in Codex, and the [shared course setup](../course-support/README.md). Run from the repository root. Seed the synthetic Lesson 2 files once; choose a fresh output directory if they already exist. PDF extraction optionally requires `pypdf`; TXT/Markdown/DOCX need no extra package.

### 5-minute quick start

```bash
python3 skills/course-support/scripts/seed_demo.py
python3 skills/local-document-organizer/scripts/course_organizer.py scan --folder .local-state/course-demo/lesson-2/incoming
```

Sample prompt:

```text
Use $local-document-organizer to preview the synthetic incoming folder, explain every move, and wait for my approval.
```

### Expected result

The preview proposes an invoice and a school document; the unknown extension stays in place. The output contains a plan path, SHA-256 fingerprint and a canonical run id. No source file has moved. These are examples, not recorded production results.

### 20–30 minute classroom exercise

Read the emitted plan and report. Approve only those moves; run `course_organizer.py apply --plan <printed-plan-path> --confirm ORGANIZE`. Inspect the action journal and moved files. Run `course_organizer.py undo --log <printed-journal-path> --confirm UNDO`, then compare file hashes to prove restoration. Resolve `workflow.py` / `course_organizer.py` command shorthand to this package's `scripts/` directory.

### What to modify

Edit `references/classification-rules.csv` to classify one extra synthetic extension; scan again. Compare proposed categories before applying. Never edit a generated approved plan. Edit the canonical package, rerun course setup, and commit only source changes to your fork.

### How to verify persistence

All course commands accept the shared storage flags before the subcommand. Start locally, then use `--storage prompthon` only after the Web App owner provisions the contract and scoped course access.

```bash
python3 skills/course-support/scripts/course_store.py runs --skill local-document-organizer
python3 skills/course-support/scripts/course_store.py read skill_runs <printed-run-id>
```

The helper performs a separate canonical GET after writes. Check organization/workspace, actor, revision and content, not only a success message. Remote mode has no SQLite fallback. [Production dependency](../course-support/references/backend-dependency.md).

### How to reset demo data

Preview `course_store.py reset`, then explicitly confirm your workspace id to clear only course records. Preserve/undo local file moves first. Source files, knowledge caches and recovery journals are not erased by record reset. Seed a new fixture folder for a clean comparison.

### Safety and approval points

The course adapter reuses existing classification rules and preview generation. Moves stay within the selected directory and use atomic no-clobber hard links before removing the old directory entry; no file contents are deleted. It fails safely on filesystems without hard-link support. It refuses stale/tampered plans, changed sources, symlinks, collisions and replayed plans. Every intent and action is fsynced in a local journal. Undo checks content hashes and refuses collisions; use `--storage local` for recovery while the remote API is down. It does not upload file binaries. Read [safety rules](references/safety-rules.md) and [source notes](references/source-notes.md).

Teaching guides: [English Lesson 2](../course-support/lessons/lesson-2.md) · [简体中文](../course-support/zh-Hans/lesson-2.md).
