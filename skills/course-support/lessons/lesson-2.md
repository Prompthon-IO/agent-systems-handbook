# Lesson 2 — Organize, Understand, Automate

English is the canonical lab. [简体中文](../zh-Hans/lesson-2.md) mirrors the same workflow and safety limits. Use synthetic files, not a real Downloads folder. On the `develop` branch, the three packages are available before a separate production handbook release.

## Learning outcomes

Organize owns file placement. Understand owns source-grounded notes. Automate owns ordered tool execution, approval points and step/run state. Students should explain those boundaries before composing the chain.

## Prepare (five minutes)

From a fresh fork/clone containing this course:

```bash
python3 skills/course-support/scripts/setup_course_skills.py --lesson 2
python3 skills/course-support/scripts/seed_demo.py
python3 skills/course-support/scripts/course_store.py context
```

The first command prints three discoverable Codex skill names. The second creates `.local-state/course-demo/lesson-2/` without replacing existing work. A seeded incoming folder contains synthetic invoice/school files and an unknown extension; the research folder contains duplicate material and conflicting capacity statements. The context is a local demo, not a signed-in production account.

## Exercise (20–30 minutes)

1. Ask `$local-document-organizer` to scan `.local-state/course-demo/lesson-2/incoming`. Inspect the plan and category counts. No files move during preview. Add one classification rule and compare a fresh preview.
2. Explicitly approve the emitted plan with `course_organizer.py apply --plan <plan-path> --confirm ORGANIZE`. Read the local action journal. Undo with `course_organizer.py undo --log <journal-path> --confirm UNDO`. Compare contents/hashes before and after; collisions must never overwrite files.
3. Ask `$personal-knowledge-capture` to synthesize `.local-state/course-demo/lesson-2/research` as `weekly-note`. Expect three source records, two unique texts, one duplicate and conflicting capacity values of 20 and 24. Inspect the source citations and do not invent which value is authoritative.
4. Change one synthetic source. Run the same note id again and compare revisions, hashes and modification times. Use Codex to improve the extractive draft while preserving references. The helper itself detects explicit field:value conflicts only.
5. Define and preview the shared workflow:

```bash
python3 skills/personal-workflow-automation/scripts/workflow.py define --file skills/personal-workflow-automation/examples/weekly-workflow.json
python3 skills/personal-workflow-automation/scripts/workflow.py preview --workflow weekly-course
```

Review the full argv list. Run with the printed SHA-256 using `run --workflow weekly-course --confirm <sha256>`. It classifies, then pauses before synthesis. After approval, use `retry --workflow weekly-course --run-id <run-id> --confirm <sha256> --approve-step synthesize`. The completed classify step is not repeated. No background task is created. An approval pause exits with code 3; it is not a completed workflow. The note uses body facts, and only configured singleton fields in `synthesis-rules.json` are checked for contradictions; independent actions are not conflicts.

All abbreviated helper commands resolve to the package's `scripts/` directory. Shared flags such as `--workspace student-02` belong before the subcommand and must be consistent across the three packages.

## Persistence and evidence

```bash
python3 skills/course-support/scripts/course_store.py runs
python3 skills/personal-knowledge-capture/scripts/course_knowledge.py show --note-id weekly-note
```

Inspect the same organization/workspace, server/local actor, status, source hashes, artifacts, events and revision. A script exit alone is not sufficient proof. With provisioned course access, put `--storage prompthon` before the subcommand and repeat canonical readback. Without that backend, remote mode must fail explicitly; a local HTTP fixture is not a Neon deployment.

## Modify and reset

Each student changes one canonical classification rule or workflow gate, reruns the setup helper, demonstrates the changed result, then commits the source change to their own fork. Do not commit `.local-state`, `.agents` generated copies, personal files or credentials.

Undo file moves before clearing course run records. Preview `course_store.py reset`; to clear only the local demo workspace rows, use `reset --confirm demo-student`. Journals and source files remain. Seed a new fixture directory to restart the file exercise without deleting old work.

## Instructor notes

Allow five minutes for setup, ten for preview/undo and source citations, ten for gates/retries, and five for evidence review. Check that students can identify a paused versus failed versus succeeded run. Inject a harmless command failure; do not retry a timed-out or interrupted step without inspecting its effects. Provision server-attested demo/course scopes before teaching remote persistence. See [backend dependency](../references/backend-dependency.md).

Remote workflow note: the sample steps explicitly set `inherit_course_access: true` for the same scoped course API. Review this flag with the manifest hash. Other steps receive no credential by default and must fail remote authentication rather than fall back to local storage. Never forward database or unrelated provider credentials.
