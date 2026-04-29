---
name: safety-escalation-review
description: Review a local evidence bundle or assistant transcript for credible harm signals, produce a redacted escalation memo and checklist, and stop before any external reporting or authority contact. Use when a user asks Codex to prepare a safety, legal, trust-and-safety, or incident handoff from local evidence.
---

# Safety Escalation Review

For the human-facing explanation, read `README.md` first. This file is the
Codex invocation contract.

## Overview

Use this skill when the user provides a local transcript, incident note, or
evidence bundle that may require safety escalation. The workflow is local-first
and review-first:

1. read the local input file
2. redact obvious direct identifiers for the memo copy
3. extract timeline cues and risk signals
4. generate a Markdown escalation memo and checklist
5. hand off to the responsible human owner

Do not contact external authorities, submit reports, message involved parties,
or upload sensitive evidence to external services unless the user gives a
separate explicit instruction and the organization policy allows it. In the
normal workflow, stop at the local memo.

## Inputs

Supported input files:

- Markdown or plain text transcripts
- JSON objects or arrays with message-like fields
- short local incident notes

Keep original evidence in the user's chosen location. Do not rewrite or move
source evidence.

## Commands

Run the helper relative to this skill directory:

```bash
python3 scripts/escalation_review.py review --input /path/to/evidence.md
```

Write to an explicit output:

```bash
python3 scripts/escalation_review.py review \
  --input /path/to/evidence.json \
  --output ~/.codex/state/safety-escalation-review/memos/case-001.md
```

Show the CLI:

```bash
python3 scripts/escalation_review.py --help
```

## Safety Rules

- Keep evidence local unless the user explicitly requests otherwise.
- Never contact law enforcement, emergency services, platform trust-and-safety
  teams, or other external parties from this skill.
- Do not decide whether the organization has a legal duty to report.
- Redact obvious emails, phone numbers, bearer tokens, and API-like secrets in
  the generated memo.
- Preserve enough source references for a human reviewer to find the original
  evidence.
- Treat a generated memo as a preparation artifact, not as the final incident
  decision.

## Human Handoff Owners

Use the user's organization language if they provide it. Otherwise suggest one
or more of:

- trust and safety
- legal
- security or incident response
- clinical or student-safety owner
- executive duty officer for urgent credible harm cases

## Outputs

By default, runtime outputs should live outside git:

```text
~/.codex/state/safety-escalation-review/
  memos/
```

The memo includes:

- case summary
- severity estimate
- detected risk signals
- timeline cues
- privacy handling notes
- human handoff checklist
- source reference

## Response Pattern

When reporting back, include:

- input path reviewed
- output memo path
- severity estimate
- key signal categories
- reminder that the memo is for human review and no external action was taken
