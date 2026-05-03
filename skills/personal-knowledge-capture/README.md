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
