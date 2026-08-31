# CRM Operations

Lesson 4 · **Operate** · `$crm-operations`

Resolve and safely create/update demo CRM contacts, deals, activity notes and follow-up tasks with revision checks and an atomic audit trail. Use for business-object operations; do not clean spreadsheets, analyze business performance or send customer messages.

Sample Codex prompt:

> Use $crm-operations in my isolated local demo workspace with the example CRM requests. Resolve existing entities and duplicates, then show the proposed contact, deal, note and follow-up changes before applying an approved plan. Ask separately before stage or close changes. Read back each object and audit trail; do not contact anyone or delete records.

## Prerequisites and five-minute quickstart

Requires the course foundation (#222), all Lesson 4 packages, Python 3.10+, and synthetic classroom data. Commands run from the handbook root. Windows users can substitute `python`/`py` for `python3`; no symlinks are required. CSV, CRM and analysis use Python standard libraries. XLSX requires the pinned `openpyxl==3.1.5` dependency from Structure's requirements.txt.

```bash
python3 skills/crm-operations/scripts/crm.py plan --request skills/crm-operations/examples/contact.json
```

Review the match, create/update operation, scope and fields. Copy the `approval_sha256` into `REVIEWED_HASH`:

```bash
python3 skills/crm-operations/scripts/crm.py apply --request skills/crm-operations/examples/contact.json --confirm REVIEWED_HASH
python3 skills/crm-operations/scripts/crm.py show contact contact-demo-alex
```

Expected: one synthetic contact, revision 1, one audit entry with actor/run/before/after. Replanning the same request returns `no_change: true`; applying that newly reviewed plan reports unchanged, not another contact.

The request uses example.invalid email addresses. No customer is contacted and no external CRM is connected.

## 20–30 minute exercise and modification

Spend 5 minutes creating the contact, 10 minutes planning/applying deal.json, activity.json and task.json in that order, 5 minutes reviewing close-deal.json without its extra approval to see the refusal, and 5 minutes granting explicit demo close approval and reading the two-entry audit. Modification: change the task due date in a copied request and compare before/after. Never send the task as a real message.

## Persistence and failure recovery

Use existing course collections `crm_contacts`, `crm_deals`, `crm_activities`, `crm_tasks` plus `skill_runs`. Each entity includes an atomic audit list with actor, time, run id, before/after and approval hash. Canonical scope/revision/readback comes from the shared Store. No third-party CRM table or separate SQLite database is introduced.

Global options precede subcommands: `--storage local|prompthon`, `--organization`, `--workspace`, `--state-dir`, `--dry-run`. Offline local mode is the default. Remote course API/auth/Neon provisioning is **not deployed by this package**; follow [shared setup](../course-support/README.md). An API error never falls back to local success. No raw workbook/CSV binary is uploaded. Fixtures use synthetic identities.

## Reset and instructor notes

Preview `python3 skills/course-support/scripts/course_store.py reset`, review all affected demo records, then add `--confirm demo-student` for that selected workspace. Reset covers all lessons' records in the workspace but never deletes source files or generated reports. Use a fresh workspace/output directory for a clean run; preserve failed outputs as evidence.

Check actual source/output hashes, canonical record revisions and audit/report evidence. A plan is not an applied change, a record save is not customer contact, and a sample metric is not a business forecast. Review source provenance and privacy before permitting `--share-rows` in remote mode.

The [English lab](../course-support/lessons/lesson-4.md) and [中文课堂指引](../course-support/zh-Hans/lesson-4.md) connect the three capabilities. Validate with `python3 -m unittest discover -s skills/business-data-structuring/tests -p 'test_*.py' -v` using the openpyxl-enabled venv. See [safety](references/safety-rules.md), [persistence](references/persistence-contract.md), and [sources](references/source-notes.md).

On a shared machine, put `--organization demo-org --workspace student-01 --state-dir .local-state/course` before every subcommand (or before source arguments in Analyze); use the same flags in readback/reset. The reset preview includes collection counts and up to 200 affected id/revision entries; inspect the truncation flag before deciding to reset.
