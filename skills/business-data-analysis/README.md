# Business Data Analysis

Lesson 4 · **Analyze** · `$business-data-analysis`

Explain a business dataset with source-backed shape, grain, quality checks, distributions, numeric summaries, descriptive metrics and next questions. Use for read-only analysis; do not rewrite source tables, operate CRM entities or make unsupported causal claims.

## Prerequisites and five-minute quickstart

Requires the course foundation (#222), all Lesson 4 packages, Python 3.10+, and synthetic classroom data. Commands run from the handbook root. Windows users can substitute `python`/`py` for `python3`; no symlinks are required. CSV, CRM and analysis use Python standard libraries. XLSX requires the pinned `openpyxl==3.1.5` dependency from Structure's requirements.txt.

First complete Structure's fixture quickstart. Then run:

```bash
python3 skills/business-data-analysis/scripts/analyze_data.py --source .local-state/course-clean/clean.json
```

Alternatively analyze the locally stored canonical dataset with `--dataset-id course-pipeline` instead of `--source`.

Expected after reviewed deduplication: 5 rows, 7 columns, 2 closed deals, closed-only win rate 0.5, open pipeline CAD 4150.00, won value CAD 3000.00, and one missing contact name/date. Compare `examples/expected-metrics.json`; the report clearly labels synthetic/descriptive evidence. Open the returned report.md path and read back its analysis id with the shared store helper.

## 20–30 minute exercise and modification

Spend 5 minutes stating grain and denominator, 10 minutes checking each metric against source rows, 5 minutes comparing the deduplicated and original input, and 5 minutes explaining which questions remain unanswered. Modification: use a copied two-currency dataset and show separate totals rather than a combined currency value. The input hash must stay unchanged.

## Persistence and failure recovery

`analysis_runs` stores the six report sections, schema/quality aggregates, source reference/hash or dataset id/revision, calculation description and report digest. `skill_runs` records execution. The helper never writes source CSV/XLSX/JSON or CRM objects; reports are new local files plus canonical analysis records. Remote metadata-only dataset records cannot be analyzed as if rows were available.

Global options precede subcommands: `--storage local|prompthon`, `--organization`, `--workspace`, `--state-dir`, `--dry-run`. Offline local mode is the default. Remote course API/auth/Neon provisioning is **not deployed by this package**; follow [shared setup](../course-support/README.md). An API error never falls back to local success. No raw workbook/CSV binary is uploaded. Fixtures use synthetic identities.

## Reset and instructor notes

Preview `python3 skills/course-support/scripts/course_store.py reset`, review all affected demo records, then add `--confirm demo-student` for that selected workspace. Reset covers all lessons' records in the workspace but never deletes source files or generated reports. Use a fresh workspace/output directory for a clean run; preserve failed outputs as evidence.

Check actual source/output hashes, canonical record revisions and audit/report evidence. A plan is not an applied change, a record save is not customer contact, and a sample metric is not a business forecast. Review source provenance and privacy before permitting `--share-rows` in remote mode.

The [English lab](../course-support/lessons/lesson-4.md) and [中文课堂指引](../course-support/zh-Hans/lesson-4.md) connect the three capabilities. Validate with `python3 -m unittest discover -s skills/business-data-structuring/tests -p 'test_*.py' -v` using the openpyxl-enabled venv. See [safety](references/safety-rules.md), [persistence](references/persistence-contract.md), and [sources](references/source-notes.md).
