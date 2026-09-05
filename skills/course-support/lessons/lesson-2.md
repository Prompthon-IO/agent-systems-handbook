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

## Optional expanded Organize practice

An instructor can choose one example, or students can complete all three in
order. The examples are independent, so work in one folder does not affect
the others. Use only the synthetic files created by these commands. Do not
practice on a real Downloads folder.

In the exercises below, a **preview** shows proposed moves without making
them, a **plan** saves those proposals for review, a **conflict** is a move
that is safely skipped, and a **journal** records what happened during
apply. See the Local Document Organizer
[beginner terminology](../../local-document-organizer/README.md#beginner-terminology)
for the other terms.

Each seed command refuses to delete or replace an existing output directory.
When repeating an exercise, keep the earlier work and add `--output` with a
fresh path, for example `--output .local-state/course-demo/student-files-attempt-2`.

### 1. Student files: preview only

**Purpose.** Learn how readable filename and extension rules produce a plan,
and see that an uncertain file stays where it is.

**Setup.** Create a fresh copy of the synthetic student-files example:

```bash
python3 skills/course-support/scripts/seed_demo.py --scenario organizer-student-files
```

**Command.** Scan the incoming folder. This command looks and proposes; it
does not move files.

```bash
python3 skills/local-document-organizer/scripts/course_organizer.py scan --folder .local-state/course-demo/lesson-2-organizer-student-files/incoming
```

**Sample Codex prompt.**

```text
Use $local-document-organizer to preview the student-files practice folder. Explain every proposed category and leave uncertain files in place. Do not move anything.
```

**Expected result.**

- `tuition-invoice.txt` -> `Invoices/`
- `school-reading.md` -> `School/`
- `internship-resume.txt` -> `Resumes/`
- `random-download.zzz` stays in place
- the preview does not move any files

**Reflection question.** Why is leaving an unknown file in place safer than
guessing a category?

### 2. Freelancer rules: customize classification

**Purpose.** See how a specific filename rule can improve a classification,
and why rule order changes the result.

**Setup.** Create a fresh copy of the synthetic freelancer example:

```bash
python3 skills/course-support/scripts/seed_demo.py --scenario organizer-freelancer-rules
```

**Command.** Generate the first preview with the default rules:

```bash
python3 skills/local-document-organizer/scripts/course_organizer.py scan --folder .local-state/course-demo/lesson-2-organizer-freelancer-rules/incoming
```

At first, `client-meeting-notes.txt` goes to `Notes` because the generic
text-extension rule matches `.txt`. In the canonical
`skills/local-document-organizer/references/classification-rules.csv`, add
this row before the generic `ext-text` rule:

```csv
keyword-meeting,Meetings,filename_keyword,meeting|minutes,medium,true
```

Before rerunning or invoking the skill, refresh the installed skill copy
from the canonical package:

```bash
python3 skills/course-support/scripts/setup_course_skills.py --lesson 2
```

Run the same scan command again to generate a fresh plan. Do not edit an
existing plan after it has been reviewed or approved.

**Sample Codex prompt.**

```text
Use $local-document-organizer to compare the freelancer practice previews before and after the Meetings rule. Explain which rule matched each file. Do not apply either plan.
```

**Expected result.**

- the invoice remains in `Invoices/`
- the agreement remains in `Contracts/`
- the meeting notes change from `Notes/` to `Meetings/`
- the website project ideas remain in `Notes/`
- rule order matters because the first matching rule wins

Restore the rule afterward if you do not intend to keep this repository
modification. If you remove the `Meetings` rule manually, run the same setup
command again so the installed copy stays synchronized.

**Reflection question.** Why must the more specific meeting rule appear
before the generic text-extension rule?

### 3. Safe recovery: conflict and undo

**Purpose.** Practice approval, collision protection, partial results, and
undo without risking real files.

**Setup.** Create a fresh copy of the synthetic safe-recovery example:

```bash
python3 skills/course-support/scripts/seed_demo.py --scenario organizer-safe-recovery
```

**Command.** Scan the incoming folder:

```bash
python3 skills/local-document-organizer/scripts/course_organizer.py scan --folder .local-state/course-demo/lesson-2-organizer-safe-recovery/incoming
```

The preview proposes moving `invoice-august.txt` to `Invoices/`. That is
only a proposal. The same-name collision is checked and enforced safely
during apply.

**Sample Codex prompt.**

```text
Use $local-document-organizer to preview the safe-recovery practice folder. Explain the proposed moves and the existing invoice collision, then wait for my explicit approval before applying anything.
```

After reviewing the preview, replace `<printed-plan-path>` with the actual
plan path printed by the scan command, including any generated identifier:

```bash
python3 skills/local-document-organizer/scripts/course_organizer.py apply --plan <printed-plan-path> --confirm ORGANIZE
```

**Expected result after apply.**

- the invoice move is recorded as `conflict`
- the existing CAD 120 invoice is not overwritten
- the revised CAD 145 invoice remains at its source
- the coffee receipt and expense notes move successfully
- the run status is `partial`
- `mystery.zzz` stays in place

Next, replace `<printed-journal-path>` with the actual journal path printed
by apply:

```bash
python3 skills/local-document-organizer/scripts/course_organizer.py undo --log <printed-journal-path> --confirm UNDO
```

**Expected result after undo.**

- successfully moved files return to their original locations
- the conflicted invoice is not incorrectly moved
- both invoice versions remain unchanged

**Reflection question.** Why does undo use the action journal instead of
trying to reverse every move from the original preview?

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

<a id="personal-knowledge-capture-learning-examples"></a>

## Personal Knowledge Capture learning examples

These three independent exercises extend the Understand practice. Allow 10–15 minutes each, or select one for class and use the others as homework. Run commands from the repository root after the shared Lesson 2 setup. They use local storage and synthetic TXT/Markdown only; no watch registration or extra package is needed.

Edit only the seeded copies under `.local-state/course-demo/`, never the tracked fixtures. If an output folder exists, seed with `--output <fresh-folder>` and substitute that folder in later commands. For a fresh version history also choose a new note id. Keep each scenario's id distinct from `weekly-note` used by the combined workflow.

### 1. Study notes: summarize and deduplicate

**Purpose.** Turn a small reading folder into a cited note without counting a copied document twice.

**Prepare and run.**

```bash
python3 skills/course-support/scripts/seed_demo.py --scenario knowledge-study-notes
python3 skills/personal-knowledge-capture/scripts/course_knowledge.py --storage local synthesize --folder .local-state/course-demo/lesson-2-knowledge-study-notes/research --note-id study-notes
python3 skills/personal-knowledge-capture/scripts/course_knowledge.py --storage local show --note-id study-notes
```

**Codex prompt.**

```text
Use $personal-knowledge-capture on .local-state/course-demo/lesson-2-knowledge-study-notes/research with local storage and note id study-notes. Explain the duplicate, show the sources behind the insights and actions, and preserve the original files. Distinguish the saved extractive draft from any further explanation you provide.
```

The prompt is an alternative way to invoke the run, not an extra required step. Running both saves another revision.

**Expected result.** Three source references, two unique texts, one duplicate, two action notes and no configured-field conflicts. Open the printed `note_path`. Trace each insight and action to its source id in Source References. The duplicate stays listed with `duplicate_of` in the stored record; neither input copy is deleted. Do not depend on which copy is designated the representative.

**Reflection.** Why retain three source references when only two distinct texts contribute insights? Text deduplication does not prove two differently worded documents say the same thing.

### 2. Workshop plans: customize conflict rules

**Purpose.** Distinguish conflicting single-value claims from compatible action items.

**Prepare and run.**

```bash
python3 skills/course-support/scripts/seed_demo.py --scenario knowledge-conflict-rules
python3 skills/personal-knowledge-capture/scripts/course_knowledge.py --storage local synthesize --folder .local-state/course-demo/lesson-2-knowledge-conflict-rules/research --note-id conflict-notes --rules .local-state/course-demo/lesson-2-knowledge-conflict-rules/rules.json
python3 skills/personal-knowledge-capture/scripts/course_knowledge.py --storage local show --note-id conflict-notes
```

Initially only `capacity` conflicts: 20 versus 24. Budget values are present in the sources but are not yet configured for conflict detection.

**Customize.** Open the seeded `.local-state/course-demo/lesson-2-knowledge-conflict-rules/rules.json`. Append `"budget"` to `single_value_fields`, preserving valid JSON and all other settings. Leave the skill's shared `references/synthesis-rules.json` unchanged. Repeat the same synthesize and show commands with the same note id and `--rules` path. No reinstall is needed because the command reads that file directly.

**Codex prompt.**

```text
In the seeded knowledge-conflict-rules exercise, add budget to the local rules.json single_value_fields and rerun $personal-knowledge-capture with local storage, note id conflict-notes and that --rules file. Compare the before/after conflicts, cite both alternatives and explain why the two action items are compatible. Do not choose an authoritative source or edit shared defaults.
```

**Expected result.** Two unique sources and no duplicates. After the edit, capacity remains 20/24 and budget adds CAD 300/CAD 450. Each alternative has source citations. Both action notes remain; they do not become a conflict. The sources remain unchanged, and the note revision increases. Reusing cached extraction does not prevent new rules from being applied.

**Reflection.** Why does adding a field change the result without editing any source? The detector checks configured `field: value` statements only; no detected conflict is not proof that the sources agree semantically.

### 3. Weekly update: follow changes and versions

**Purpose.** Separate a new save from an actual source change.

**Prepare and run.**

```bash
python3 skills/course-support/scripts/seed_demo.py --scenario knowledge-weekly-update
python3 skills/personal-knowledge-capture/scripts/course_knowledge.py --storage local synthesize --folder .local-state/course-demo/lesson-2-knowledge-weekly-update/research --note-id weekly-update-notes
python3 skills/personal-knowledge-capture/scripts/course_knowledge.py --storage local show --note-id weekly-update-notes
```

Record the revision and each source's `sha256`, `modified_ns` and `change`. Repeat synthesize and show without edits: both sources now say `unchanged`, hashes stay the same, and the revision increases.

Next edit only the seeded `research/weekly-update.txt`: replace `Completed examples: 2` with `Completed examples: 3`. Repeat the same two commands a third time, using `weekly-update-notes` again.

**Codex prompt.**

```text
Use $personal-knowledge-capture with local storage and note id weekly-update-notes on .local-state/course-demo/lesson-2-knowledge-weekly-update/research. Compare the current run with the prior result: explain which source changed, check its hash and citations, and distinguish source changes from note revisions. Do not modify the source files yourself.
```

**Expected result.** The edited file says `modified` and has a different hash; `project-brief.md` stays `unchanged` with its original hash. The note reflects three completed examples with a valid source reference. Two unique sources, zero duplicates and no configured-field conflicts remain. A fresh note id progresses through revisions 1, 2 and 3; existing ids continue from their current revision. The Markdown file is the latest draft and is overwritten on each save, so retain the displayed before/after evidence for comparison.

**Reflection.** Does a newer timestamp prove a source is more authoritative? No. Does a higher note revision prove the facts changed? No: unchanged inputs also produce a new saved revision.

### Verify the exercises

Use the printed `note_path` and the `show` readback to check content and references, not just exit status. A source id identifies an input; a hash fingerprints its content; a revision identifies a saved version. Compare source hashes before and after each helper run: only the student's deliberate edit in exercise 3 should change file content. Keep all state and notes outside git.

The saved output is an extractive draft, not a full semantic analysis. Codex refinements must retain citations and must not be described as persisted course changes unless separately saved and verified. These exercises need no remote service and do not change workflow approval gates.

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
