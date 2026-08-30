# AI Search Visibility

Lesson 5 · **Discover** · `$ai-search-visibility`

Audit selected page snapshots for target-question answerability, entity positioning, headings, evidence and cross-page consistency, then recheck the same scope after edits. Use for AEO content review; do not promise search ranking, AI citations, indexing or publication.

## Prerequisites and five-minute quickstart

Requires the course foundation (#222), Lesson 5 packages and Python 3.10+. Commands run from the handbook root; Windows users may substitute `python`/`py` for `python3`. Use synthetic fixtures and an isolated student workspace. Social browser-adapter contract tests also need Node.js; actual browser execution needs separately provisioned demo backend capability and a signed-in Host session.

```bash
python3 skills/ai-search-visibility/scripts/aeo_audit.py --site skills/ai-search-visibility/examples/site --spec skills/ai-search-visibility/examples/audit-spec.json
python3 skills/course-support/scripts/course_store.py read aeo_audits course-aeo
```

Expected: five structural findings in the imperfect two-page fixture: missing entity introduction, skipped heading level, missing evidence attribution, an unanswered build question, and conflicting duration values (90/120 minutes). Each finding has source evidence or explicitly notes the missing signal. Files remain unchanged; no site was fetched, indexed or published.

## 20–30 minute exercise and one modification

Spend 5 minutes reviewing the target questions, 10 minutes checking findings against both pages, 5 minutes correcting a copy of the duration/entity/heading/build-answer issues using the synthetic brief, and 5 minutes rerunning the same audit id with --expected-revision 1. Modification: change the target-query set and observe that removed findings are not called resolved. Evidence quality still requires human judgment.

## Persistence, readback and recovery

`aeo_audits` stores target queries, scope hash, page source hashes/URLs, structural signals, short evidence excerpts, findings, recommendations and recheck comparison under a stable audit id/revision. `skill_runs` records each audit. Local snapshots are never uploaded as raw HTML, and the audit does not modify them. New reports are saved separately.

Select global `--storage local|prompthon`, organization, workspace and state directory before subcommands; use the same scope for readback. The default is local/offline. Remote API/auth/Neon deployment is not created by installing these packages. A failed remote write does not silently become local success. See [shared setup](../course-support/README.md).

Read runs with `python3 skills/course-support/scripts/course_store.py runs --skill ai-search-visibility`. Every reported id must come from the actual tool response; fixture domains and mock receipts are not live results.

## Reset and instructor notes

Preview the shared `course_store.py reset`, review its scope, then confirm the selected demo workspace with `--confirm demo-student`. It removes all course records in that workspace, not files, web pages, canonical Social campaigns/posts or external deliveries. Use a fresh workspace for repeat exercises and the owning app's separately authorized cleanup flow for actual Social objects; never silently delete them.

Review the actual source, plan, canonical records and audit/report evidence. A content calendar is not a schedule; a course simulation is not public publication; an AEO heuristic is not measured ranking. [English lab](../course-support/lessons/lesson-5.md) · [中文课堂指引](../course-support/zh-Hans/lesson-5.md).

Validate with `python3 -m unittest discover -s skills/content-strategy/tests -p 'test_*.py' -v`. This includes an entirely mocked Node Social contract harness; no external delivery is performed. See [safety](references/safety-rules.md), [persistence](references/persistence-contract.md), and [sources](references/source-notes.md).
