# Personal Knowledge Capture

## Why This Skill Exists

This package is a Practitioner-facing workflow for turning local research files into searchable, cited Markdown notes.

"Summarize my research folder" is not a single prompt problem once the workflow needs durable watch paths, incremental detection, file hashing, document parsing, source references, and repeated notes across sessions. This skill keeps those deterministic parts in a local helper script and leaves synthesis to Codex.

## Who It Is For

This skill is for students, contributors, and operators who collect local research material and want a repeatable way to capture what changed.

It is most useful for requests such as:

- watch my AI research folder
- summarize files I added today
- turn new Markdown, TXT, DOCX, or PDF files into cited notes
- keep a local SQLite record of captured sources

## End-to-End Workflow

The workflow is local-first and explicit:

1. Register a folder the user names.
2. Scan only registered folders.
3. Detect new or modified files by path and SHA-256 hash.
4. Extract text where supported.
5. Write a dated Markdown note with source references.
6. Keep runtime state outside the repository by default.

## What The Package Actually Does

The helper script supports:

- `add-watch` for persistent watch-path registration
- `scan` for new and modified source detection previews
- `summarize` for scan-and-write dated Markdown note generation
- `capture-url` for explicitly provided URLs

The generated Markdown note uses the required section structure:

```md
# Summary

## New Files

## Key Insights

## Actionable Notes

## Open Questions

## Source References
```

## What It Does Not Do

This package does not:

- run a live background watcher
- scan unregistered folders
- upload local files to external services
- move or rewrite source files
- commit runtime databases or generated notes

## Status And Maintenance

This is a first-version local helper. Maintain it as a deterministic scanner and note writer: keep runtime state outside git, keep new extractors optional unless they use the Python standard library, and update `references/supported-file-types.md` when file type support changes.

## How To Read It In The Handbook

Treat this package as a Practitioner example of a local knowledge workflow:

- `README.md` explains the human story and workflow
- `SKILL.md` explains the Codex invocation contract
- `scripts/personal_knowledge_capture.py` implements deterministic local state and scanning
- `references/supported-file-types.md` documents extraction boundaries

## Professional AI Agent Course: Understand

### What you will learn

Extract and deduplicate selected sources into a cited note, flag contradictions and track changes. Never relocate source files.

### Prerequisites

Use Python 3.10+, a fork/clone opened in Codex, and the [shared course setup](../course-support/README.md). Run from the repository root. Seed the synthetic Lesson 2 files once; choose a fresh output directory if they already exist. PDF extraction optionally requires `pypdf`; TXT/Markdown/DOCX need no extra package.

### 5-minute quick start

```bash
python3 skills/personal-knowledge-capture/scripts/course_knowledge.py synthesize --folder .local-state/course-demo/lesson-2/research --note-id weekly-note
python3 skills/personal-knowledge-capture/scripts/course_knowledge.py show --note-id weekly-note
```

Sample prompt:

```text
Use $personal-knowledge-capture on the course research folder; deduplicate repeated sources, surface the conflicting capacity claims and create a cited weekly note without changing originals.
```

### Expected result

Three sources produce two unique texts, one duplicate and a capacity conflict (20 versus 24), with source ids/hashes and actionable notes. Repeating the run marks unchanged sources and increments the same note revision. These are examples, not recorded production results.

### 20–30 minute classroom exercise

Ask Codex to inspect the source-grounded extractive draft and distinguish the two capacity claims. Explain which source is authoritative without guessing. Edit only a synthetic source, rerun and compare the note revision, changed-source metadata and citations. Source file hashes must remain unchanged by the helper. Resolve `workflow.py` / `course_organizer.py` command shorthand to this package's `scripts/` directory.

### What to modify

Change a synthetic capacity or action line; add a semantically conflicting sentence without a field label. Observe that deterministic field checks have limits and use Codex to cite the semantic conflict. Edit the canonical package, rerun course setup, and commit only source changes to your fork.

### How to verify persistence

All course commands accept the shared storage flags before the subcommand. Start locally, then use `--storage prompthon` only after the Web App owner provisions the contract and scoped course access.

```bash
python3 skills/course-support/scripts/course_store.py runs --skill personal-knowledge-capture
python3 skills/course-support/scripts/course_store.py read skill_runs <printed-run-id>
```

The helper performs a separate canonical GET after writes. Check organization/workspace, actor, revision and content, not only a success message. Remote mode has no SQLite fallback. [Production dependency](../course-support/references/backend-dependency.md).

### How to reset demo data

Preview `course_store.py reset`, then explicitly confirm your workspace id to clear only course records. Preserve/undo local file moves first. Source files, knowledge caches and recovery journals are not erased by record reset. Seed a new fixture folder for a clean comparison.

### Safety and approval points

Only the named folder is scanned; source files are never modified. Incremental extraction caches remain local and are keyed by content hash and modification time. Remote notes contain derived extractive summaries and source metadata, not original binaries or the complete extracted text. `--share-content` is an explicit extra opt-in for extracted text; review privacy first. The deterministic conflict detector only recognizes field:value disagreements and does not assign authority automatically. Read [safety rules](references/safety-rules.md) and [source notes](references/source-notes.md).

Teaching guides: [English Lesson 2](../course-support/lessons/lesson-2.md) · [简体中文](../course-support/zh-Hans/lesson-2.md).

The course adapter skips document headings when drafting body insights. Configure singleton facts versus independent action fields in `references/synthesis-rules.json`, or pass `synthesize --rules <file>`. Only singleton disagreements are flagged; compatible actions remain separate action notes.
