# Deep Research Agent Starter

## Summary

This starter turns the deep-research case study into a small project skeleton
centered on planning, evidence collection, and citation-aware synthesis.

## Status

`starter`

## Why It Exists

Deep research is a flagship agent product shape in this repo. A small starter
makes it easier to contribute traces, artifacts, and evaluation ideas later
without copying a full external implementation.

## Related Lab Pages

- [Deep Research Agents](../../deep-research-agents.md)
- [Case Studies Overview](../../README.md)

## Folder Structure

```text
deep-research-agent-starter/
├── README.md
├── SOURCE_NOTES.md
└── src/
    ├── citation_formatter.py
    ├── research_loop.py
    └── research_review.py
```

## Quick Start

This is a starter, not a finished product. The code sketch focuses on the core
loop and leaves transport, UI, and persistence out of scope. For a repo-level
smoke check, run `python3 scripts/verify_example_projects.py` from the
repository root.

## Included Sample Files

- `src/research_loop.py`: the minimal planning, evidence, and draft-report loop
- `src/citation_formatter.py`: a tiny reference surface for turning evidence
  rows into readable citations
- `src/research_review.py`: a small post-research quality check for evidence
  coverage before publication

## Constraints

- No search adapter is implemented.
- Citation formatting is illustrative.
- Artifact persistence is not wired yet.

## Next Steps

- Add a real evidence store.
- Add a report artifact writer.
- Add evaluation cases for missing or weak evidence.
