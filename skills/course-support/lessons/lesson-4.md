# Lesson 4 — Structure → Operate → Analyze

Outcome: a reviewed clean dataset, four kinds of demo CRM object with audit history, and a read-only evidence report. These are separate jobs, not three names for editing a spreadsheet.

## Before class and five-minute start

Install `--lesson 4` with the shared setup script. Use a separate workspace per student, Python 3.10+ and Structure's pinned openpyxl dependency for XLSX. All identities are synthetic; no external CRM, real customer data or email service is needed. Run [Structure's quickstart](../../business-data-structuring/README.md) and inspect the plan before applying its hash to a new output directory.

## 25-minute exercise

1. Minutes 0–8: normalize the fixture CSV with its explicit schema. After reviewed exact deduplication, expect 6→5 rows and 7 columns; keep nulls visible. Generate the XLSX fixture and compare parsed rows.
2. Minutes 8–17: use [Operate](../../crm-operations/README.md) to plan/apply contact, deal, activity and follow-up task fixtures one at a time. Inspect id/revision/audit. Review a close-deal request; demonstrate refusal without extra high-impact approval, then explicitly approve the synthetic change and read it back.
3. Minutes 17–25: run [Analyze](../../business-data-analysis/README.md) on clean.json. Verify the 0.5 closed-only win rate and CAD 4150 open pipeline from source rows. Explain the missing name/date, row grain and denominator instead of making causal claims.

Modification: preserve the duplicate and compare totals, or introduce a second currency in a copy and confirm it is reported separately. Change a task due date and compare its audit before/after; do not send a real message.

## Evidence, reset and instructor review

Collect unchanged source hash, review plan hash, clean output hashes, canonical dataset id/revision, CRM audit and analysis id/report. Structure's remote default is metadata only; normalized row sharing must be explicit and synthetic. Missing backend provisioning is not a successful remote save.

Reset the selected demo workspace using shared reset preview/confirmation; it clears all course records there, not original files or reports. Use a fresh directory/workspace for repeat exercises. No destructive file rewrite, silent record delete, customer send, currency conversion or production CRM operation is part of this lab.
