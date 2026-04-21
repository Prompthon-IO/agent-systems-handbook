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

## Related Handbook Pages

- [Deep Research Agents](../../deep-research-agents.md)
- [Case Studies Overview](../../README.md)

## Folder Structure

```text
deep-research-agent-starter/
├── README.md
├── SOURCE_NOTES.md
└── src/
    └── research_loop.py
```

## Quick Start

This is a starter, not a finished product. The code sketch focuses on the core
loop and leaves transport, UI, and persistence out of scope.

## Constraints

- No search adapter is implemented.
- Citation formatting is illustrative.
- Artifact persistence is not wired yet.

## Next Steps

- Add a real evidence store.
- Add a report artifact writer.
- Add evaluation cases for missing or weak evidence.
