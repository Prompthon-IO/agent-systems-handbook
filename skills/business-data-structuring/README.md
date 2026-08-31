# Business Data Structuring

Lesson 4 · **Structure** · `$business-data-structuring`

Inspect messy CSV/XLSX tables and create a reviewed clean business dataset with normalized headers, types, dates and amounts. Use for preparing a table; do not operate CRM entities or turn the preparation step into business analysis.

Sample Codex prompt:

> Use $business-data-structuring on the synthetic pipeline fixture and its schema. Explain the headers, types, nulls and duplicate before proposing cleanup. Show the exact plan hash for review, then write only to a new output directory after approval. Verify that the source is unchanged and read back the saved dataset.

## Prerequisites and five-minute quickstart

Requires the course foundation (#222), all Lesson 4 packages, Python 3.10+, and synthetic classroom data. Commands run from the handbook root. Windows users can substitute `python`/`py` for `python3`; no symlinks are required. CSV, CRM and analysis use Python standard libraries. XLSX requires the pinned `openpyxl==3.1.5` dependency from Structure's requirements.txt.

```bash
python3 skills/course-support/scripts/setup_course_skills.py --lesson 4
python3 skills/business-data-structuring/scripts/structure_data.py preview --source skills/business-data-structuring/examples/messy-pipeline.csv --schema skills/business-data-structuring/examples/schema.json --dedupe
```

Review the preview and copy its `plan_sha256`. Replace `REVIEWED_HASH` below with that exact value:

```bash
python3 skills/business-data-structuring/scripts/structure_data.py apply --source skills/business-data-structuring/examples/messy-pipeline.csv --schema skills/business-data-structuring/examples/schema.json --dedupe --output .local-state/course-clean --confirm REVIEWED_HASH
```

Expected: 6 input rows, 5 output rows, 7 columns, 1 exact duplicate, no parse errors; output contains clean.csv, clean.json and review.json. Missing contact name and close date remain explicit nulls. The original file is unchanged.

For XLSX, install `requirements.txt` in the course venv, then generate a synthetic workbook with `python3 skills/business-data-structuring/scripts/make_xlsx_fixture.py --output .local-state/demo-pipeline.xlsx`. Use the same preview command with that source. Both formats should produce equivalent normalized rows.

## 20–30 minute exercise and modification

Spend 5 minutes identifying grain and null/duplicate issues, 10 minutes reviewing the schema and clean output, 5 minutes repeating with the generated XLSX, and 5 minutes changing the date format incorrectly to see a refusal. Modification: keep duplicates by omitting --dedupe and compare row counts before deciding whether a real dataset allows removal.

## Persistence and failure recovery

`business_datasets` holds schema, grain, source hash, shape, null/duplicate/error inspection, plan hash and local output references/hashes. Local mode also stores normalized rows; remote row sharing is explicit. `skill_runs` records the operation. Output is written before registration so a failed remote write leaves recoverable local evidence; it is not a successful remote save.

Global options precede subcommands: `--storage local|prompthon`, `--organization`, `--workspace`, `--state-dir`, `--dry-run`. Offline local mode is the default. Remote course API/auth/Neon provisioning is **not deployed by this package**; follow [shared setup](../course-support/README.md). An API error never falls back to local success. No raw workbook/CSV binary is uploaded. Fixtures use synthetic identities.

## Reset and instructor notes

Preview `python3 skills/course-support/scripts/course_store.py reset`, review all affected demo records, then add `--confirm demo-student` for that selected workspace. Reset covers all lessons' records in the workspace but never deletes source files or generated reports. Use a fresh workspace/output directory for a clean run; preserve failed outputs as evidence.

Check actual source/output hashes, canonical record revisions and audit/report evidence. A plan is not an applied change, a record save is not customer contact, and a sample metric is not a business forecast. Review source provenance and privacy before permitting `--share-rows` in remote mode.

The [English lab](../course-support/lessons/lesson-4.md) and [中文课堂指引](../course-support/zh-Hans/lesson-4.md) connect the three capabilities. Validate with `python3 -m unittest discover -s skills/business-data-structuring/tests -p 'test_*.py' -v` using the openpyxl-enabled venv. See [safety](references/safety-rules.md), [persistence](references/persistence-contract.md), and [sources](references/source-notes.md).

On a shared machine, put `--organization demo-org --workspace student-01 --state-dir .local-state/course` before every subcommand (or before source arguments in Analyze); use the same flags in readback/reset. The reset preview includes collection counts and up to 200 affected id/revision entries; inspect the truncation flag before deciding to reset.
