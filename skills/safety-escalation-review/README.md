# Safety Escalation Review

## Why This Skill Exists

Assistant systems sometimes produce or receive evidence that suggests credible
harm, violence, self-harm, stalking, extortion, or other high-risk behavior.
Those cases should not be handled as ordinary summarization tasks.

This practitioner skill teaches a local-first review pattern:

1. collect a local evidence bundle
2. normalize and redact obvious private details
3. extract timeline and risk signals
4. draft an escalation memo and checklist
5. hand the result to the human legal, trust-and-safety, security, or incident
   owner

The skill does not contact authorities, submit reports, or decide legal duties.
It creates a review artifact that helps humans make the next decision.

## Who It Is For

This package is for students, contributors, operators, and builders who need a
small example of safety-review workflow design. It is useful when someone has a
transcript, local incident note, or JSON evidence bundle and needs a consistent
way to summarize what happened without moving sensitive data off-machine.

## End-to-End Workflow

1. Save the transcript or evidence bundle locally.
2. Run the helper script against that local file.
3. Review the generated Markdown memo.
4. Give the memo to the responsible human owner.
5. Keep runtime evidence and reports out of git.

Example:

```bash
python3 scripts/escalation_review.py \
  review \
  --input /path/to/evidence.md \
  --output ~/.codex/state/safety-escalation-review/memos/case-001.md
```

## What The Helper Checks

The helper looks for basic textual signals such as:

- explicit violence or weapon terms
- named targets, locations, or timing cues
- self-harm or distress language
- evasion, repeat-account, or ban-circumvention clues
- privacy-sensitive identifiers that should be redacted in the memo

These checks are intentionally simple. They make the review repeatable, not
authoritative.

## What It Does Not Do

This package does not:

- contact law enforcement or external services
- upload evidence to a model provider
- make legal determinations
- replace trust-and-safety, legal, security, or clinical judgment
- store private transcripts in the public repository

## How To Read It In The Handbook

Treat this package as a code-plus-docs example of an escalation workflow. The
important pattern is the split between deterministic local preparation and
human ownership of the final decision.
