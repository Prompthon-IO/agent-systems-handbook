---
name: garbage-collector
description: Scan local cleanup targets, apply readable cleanup rules, produce a preview report, and execute approved cleanup actions with logs. Use when a user asks Codex to clean up their computer, empty old Trash items, find duplicated Downloads files, review local storage clutter, or propose safe file cleanup actions before making changes.
---

# Garbage Collector

For a student-facing explanation of why this package exists and how the
end-to-end workflow fits into the handbook, read `README.md` first. This file
is the invocation contract for Codex.

## Overview

Use this skill to propose and execute safe local cleanup tasks. The skill is
preview-first: scan the requested paths, show cleanup suggestions, wait for
explicit user approval, then run only the approved cleanup actions.

The initial rule store is `references/cleanup-rules.csv`. Keep rules readable
by people and agents; a later implementation can migrate them into SQLite if
the workflow needs richer history or per-user state.

## Safety Rules

- Never delete, move, or overwrite files during the preview step.
- Never scan `/`, system folders, external drives, or cloud-sync folders unless
  the user names them explicitly.
- Treat "scan my computer" as `~/Downloads` and `~/.Trash` first, plus any
  user-approved extra paths.
- Require explicit approval before cleanup. If the cleanup includes permanent
  deletion from Trash, require a separate destructive confirmation.
- Prefer reversible actions. Duplicate Downloads cleanup should move duplicate
  files into a quarantine folder inside the OS Trash, not permanently delete
  them.
- Log every applied action and keep enough information to support undo where
  possible.

## Default Workflow

1. Read `references/cleanup-rules.csv`.
2. Ask for or infer a safe scan target. Default to `~/Downloads` and
   `~/.Trash` when the user says "my computer" without more detail.
3. Run a preview scan with `scripts/garbage_collector.py scan`.
4. Summarize the generated Markdown report for the user.
5. If the user approves, run `scripts/garbage_collector.py apply` against the
   generated plan file.
6. Report applied actions, skipped actions, and the undo log path.

## Commands

Resolve `scripts/garbage_collector.py` relative to this skill directory. When
running from an installed Codex copy, that is usually
`~/.codex/skills/garbage-collector/scripts/garbage_collector.py`.

Preview the default targets:

```bash
python3 scripts/garbage_collector.py scan
```

Preview a specific folder:

```bash
python3 scripts/garbage_collector.py scan --target "$HOME/Downloads"
```

Apply a generated plan after user approval:

```bash
python3 scripts/garbage_collector.py apply --plan /path/to/plan.json --confirm CLEANUP
```

Apply a plan that includes permanent Trash deletion only after explicit
destructive confirmation:

```bash
python3 scripts/garbage_collector.py apply \
  --plan /path/to/plan.json \
  --confirm CLEANUP \
  --allow-permanent-delete
```

Undo reversible move actions from an action log:

```bash
python3 scripts/garbage_collector.py undo --log /path/to/actions.json
```

## Initial Rules

The first two rule families are:

- `trash-can`: suggest permanent cleanup for files already in the OS Trash,
  with an age threshold.
- `duplicate-downloads`: find duplicate files in Downloads by size and SHA-256
  hash, keep one copy, and move extra copies to a quarantine folder in Trash
  only after approval.

Add new rules by extending `references/cleanup-rules.csv`. Keep `rule_id`,
`scope`, `default_action`, and `rule_text` clear enough for another Codex run
to understand without hidden context.

## Outputs

The helper writes local runtime artifacts under:

```text
~/.codex/state/garbage-collector/
  reports/
  plans/
  logs/
```

Do not commit runtime reports, plans, or logs unless the user explicitly asks
for sample artifacts.

## Response Pattern

When reporting results to the user, include:

- scan targets
- number of suggestions
- estimated reclaimable size
- high-risk actions, if any
- report path
- plan path
- what confirmation is needed before cleanup
