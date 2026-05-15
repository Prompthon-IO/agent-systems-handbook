---
name: local-document-organizer
description: Preview-first local file organizer. Scan a user-named folder, classify files into category subfolders using readable rules, write a preview Markdown report and JSON plan, execute confirmed moves with persistent SQLite state, and reverse moves with undo. Use when a user asks Codex to organize Downloads, sort a messy folder into Invoices/Receipts/School/Images/Software/PDFs subfolders, propose a folder structure before moving anything, or undo a previous organization run.
---

# Local Document Organizer

For a student-facing explanation of why this package exists and how the
preview-then-apply workflow fits into the handbook, read `README.md` first.
This file is the invocation contract for Codex.

## Overview

Use this skill to propose and execute safe local file organization. The skill
is preview-first and confirmation-gated: scan the user-named folder, write a
proposed category structure as a Markdown report and a JSON plan, wait for
explicit user approval, then run only the approved moves. Every applied move
is logged so it can be reversed with `undo`.

The skill never deletes and never overwrites. See `references/safety-rules.md`
for the full safety contract.

## Safety Rules

- Never delete files. The script does not call `unlink` or `rmtree`.
- Never overwrite files. Destination collisions are skipped and logged as
  `conflict`.
- Never move files before the user approves the preview and supplies
  `--confirm ORGANIZE`.
- Refuse to scan `/`, `/System`, `/Library`, `/Applications`, `~/Library`,
  `~/.ssh`, `~/.gnupg`, `~/.aws`, or the home directory itself. The user must
  name a subfolder.
- Treat low-confidence and unmatched files as `Unknown/` and skip them by
  default; they are surfaced in the preview report so the user can opt in
  with `--include-low-confidence`.
- Permission errors and name collisions are recorded as skipped actions, not
  silent failures; one skipped file does not abort the whole run.
- Runtime database, plans, action logs, and reports stay under
  `~/.codex/state/local-document-organizer/` and are not committed to git.

## Default Workflow

1. Confirm with the user which folder to scan. Default to `~/Downloads` only
   if the user explicitly says so; otherwise ask.
2. Run `scripts/local_document_organizer.py scan --folder <path>`.
3. Read the generated Markdown report aloud to the user, including the
   per-category counts and any skipped or low-confidence files.
4. Wait for explicit user approval. Do not invoke `apply` from inferred
   consent.
5. On approval, run
   `scripts/local_document_organizer.py apply --plan <plan.json> --confirm ORGANIZE`.
6. Report applied moves, conflicts, missing files, and the action log path so
   the user knows where the undo log lives.
7. If the user asks to revert, run
   `scripts/local_document_organizer.py undo --log <log.json>`.

## Commands

Resolve `scripts/local_document_organizer.py` relative to this skill
directory. When running from an installed Codex copy, that is usually
`~/.codex/skills/local-document-organizer/scripts/local_document_organizer.py`.

Preview a folder:

```bash
python3 scripts/local_document_organizer.py scan --folder "$HOME/Downloads"
```

Preview including low-confidence and hidden files:

```bash
python3 scripts/local_document_organizer.py scan \
  --folder "$HOME/Downloads" \
  --include-low-confidence \
  --include-hidden
```

Apply a generated plan after explicit user approval:

```bash
python3 scripts/local_document_organizer.py apply \
  --plan ~/.codex/state/local-document-organizer/plans/<run_id>-plan.json \
  --confirm ORGANIZE
```

Reverse the moves from a run:

```bash
python3 scripts/local_document_organizer.py undo \
  --log ~/.codex/state/local-document-organizer/logs/<run_id>-actions.json
```

List recent runs:

```bash
python3 scripts/local_document_organizer.py runs --limit 10
```

## Classification Rules

Rules live in `references/classification-rules.csv` and are evaluated in CSV
order; first match wins. Filename-keyword rules sit above extension rules so
that, for example, `invoice-uber-2026-04.pdf` is classified as `Invoices`
rather than the generic `PDFs` bucket.

Each row has columns: `rule_id, category, match_type, pattern, confidence,
enabled`. `match_type` is `extension` or `filename_keyword`. `pattern` is a
`|`-separated list of tokens (extensions without the dot, or whole-word
keywords matched at word boundaries). `confidence` is `high`, `medium`, or
`low`; only `high` and `medium` matches are eligible to move by default.

Add new rules by extending the CSV. Keep `rule_id` stable so action logs and
report tables remain meaningful across edits.

## Persistence

The SQLite database lives at:

```text
~/.codex/state/local-document-organizer/organizer.sqlite
```

Schema:

```sql
organizer_runs(id, folder_path, created_at, status)
file_actions(id, run_id, old_path, new_path, action, confidence)
```

`organizer_runs.status` is one of: `previewed`, `applying`, `ok`, `partial`,
`no_moves`. `file_actions.action` is one of: `moved`, `conflict`, `missing`,
`permission_error`, `failed`.

## Outputs

```text
~/.codex/state/local-document-organizer/
  organizer.sqlite
  reports/YYYY-MM-DD-<folder-name>.md
  plans/<run_id>-plan.json
  logs/<run_id>-actions.json
```

Do not commit runtime artifacts unless the user explicitly asks for sample
files.

## Response Pattern

When reporting `scan` results to the user, include:

- folder scanned
- proposed category structure (per-category counts and total size)
- any low-confidence or skipped files that the user might want to include
- the report and plan paths
- a clear next step: "approve to apply, or ask me to refine the rules"

When reporting `apply` results, include:

- run status (`ok`, `partial`, or `no_moves`)
- moved, conflict, missing, permission, and failed counts
- the action log path so the user can run `undo` later if they change their
  mind

When reporting `undo` results, include the restored count and any skipped
files (e.g. because the original path now contains a different file).
