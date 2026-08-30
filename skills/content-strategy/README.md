# Content Strategy

Lesson 5 · **Plan** · `$content-strategy`

Develop and iterate a content strategy with business goal, audience, pillars, searchable/shareable topics, priorities and an editorial calendar. Use before drafting a campaign; do not schedule posts or treat editorial judgments as measured search demand.

## Prerequisites and five-minute quickstart

Requires the course foundation (#222), Lesson 5 packages and Python 3.10+. Commands run from the handbook root; Windows users may substitute `python`/`py` for `python3`. Use synthetic fixtures and an isolated student workspace. Social browser-adapter contract tests also need Node.js; actual browser execution needs separately provisioned demo backend capability and a signed-in Host session.

```bash
python3 skills/course-support/scripts/setup_course_skills.py --lesson 5
python3 skills/content-strategy/scripts/strategy.py preview --brief skills/content-strategy/examples/workshop-strategy.json
```

Review the priorities/calendar, then replace REVIEWED_HASH with the returned plan_sha256:

```bash
python3 skills/content-strategy/scripts/strategy.py save --brief skills/content-strategy/examples/workshop-strategy.json --confirm REVIEWED_HASH
python3 skills/content-strategy/scripts/strategy.py show --strategy-id workshop-strategy
```

Expected: four topics grouped under three pillars, both searchable/shareable intent, four offset-aware calendar entries, revision 1, and `external_scheduling: false`. The practice-story topic is explicitly unvalidated. On Windows, install the `tzdata` Python package if the system does not provide IANA timezone data.

Sample Codex prompt:

> Use $content-strategy with the synthetic workshop brief in this package. Explain the pillars and topic priorities, identify unsupported assumptions, and preview a calendar in my local demo workspace. Show the reviewed plan hash before saving. Continue the same strategy id when I revise a score; do not schedule or publish content.

## 20–30 minute exercise and one modification

Spend 5 minutes reviewing goal/audience, 10 minutes challenging topic scores and source support, 5 minutes saving and reading the strategy, and 5 minutes changing one topic score in a copied brief. Preview/save the same strategy with --expected-revision 1, then compare revision 2 and its calendar. Do not silently reuse revision 0 or call planned items scheduled.

## Persistence, readback and recovery

`content_strategies` stores the brief, pillars, clusters, ranked topics, evidence references, editorial scores and calendar under a stable strategy id with revision CAS. Each save has a `skill_runs` entry and a local revision snapshot. A subsequent campaign records the strategy id/revision in the existing Social campaign metadata.

Select global `--storage local|prompthon`, organization, workspace and state directory before subcommands; use the same scope for readback. The default is local/offline. Remote API/auth/Neon deployment is not created by installing these packages. A failed remote write does not silently become local success. See [shared setup](../course-support/README.md).

Read runs with `python3 skills/course-support/scripts/course_store.py runs --skill content-strategy`. Every reported id must come from the actual tool response; fixture domains and mock receipts are not live results.

## Reset and instructor notes

Preview the shared `course_store.py reset`, review its scope, then confirm the selected demo workspace with `--confirm demo-student`. It removes all course records in that workspace, not files, web pages, canonical Social campaigns/posts or external deliveries. Use a fresh workspace for repeat exercises and the owning app's separately authorized cleanup flow for actual Social objects; never silently delete them.

Review the actual source, plan, canonical records and audit/report evidence. A content calendar is not a schedule; a course simulation is not public publication; an AEO heuristic is not measured ranking. [English lab](../course-support/lessons/lesson-5.md) · [中文课堂指引](../course-support/zh-Hans/lesson-5.md).

Validate with `python3 -m unittest discover -s skills/content-strategy/tests -p 'test_*.py' -v`. This includes an entirely mocked Node Social contract harness; no external delivery is performed. See [safety](references/safety-rules.md), [persistence](references/persistence-contract.md), and [sources](references/source-notes.md).
