# Garbage Collector

## Why This Skill Exists

This package is a Practitioner-facing workflow example for safe local cleanup.

It exists because "clean up my computer" sounds simple in chat, but it becomes
dangerous quickly if an agent starts deleting files without a preview, clear
rules, or explicit approval.

The package demonstrates a better pattern:

- preview first
- explain the findings
- wait for approval
- apply only the approved actions
- keep enough logs to support undo where possible

## Who It Is For

This skill is for students, contributors, and operators who want to understand
what a real Codex-compatible local workflow looks like when file safety matters.

It is most useful for requests such as:

- scan Downloads for duplicates
- inspect Trash before permanent deletion
- propose safe cleanup actions before changing anything

## End-to-End Workflow

The workflow is intentionally cautious:

1. Choose a safe target such as `~/Downloads` or `~/.Trash`.
2. Run a scan to produce a preview report.
3. Review the report with the user.
4. Generate or inspect the proposed action plan.
5. Apply only after explicit approval.
6. Keep logs so reversible actions can be undone later.

That is the main teaching point of the package. The skill is not just "delete
files." It is a human-reviewed cleanup workflow with explicit risk boundaries.

## What The Package Actually Does

The package currently focuses on two rule families:

- old files already in Trash
- duplicate files in Downloads

It uses readable rules and a deterministic helper script rather than hidden
heuristics. The output is meant to be inspectable by a human before anything is
applied.

## What It Does Not Do

This package does not:

- auto-delete files during the preview step
- scan the whole machine by default
- silently operate on system folders or cloud-sync folders
- treat destructive cleanup as a one-click default

## How To Read It In The Handbook

Treat this package as a Practitioner example of a local, safety-sensitive
workflow:

- `README.md` explains the human story and the end-to-end process
- `SKILL.md` explains when Codex should invoke the package
- `scripts/garbage_collector.py` implements the deterministic helper

If you are a student reading the repo, the main lesson is:

1. local workflows need explicit guardrails
2. reversible preview-first behavior is often better than direct action
3. a good skill package should make that operational logic legible
