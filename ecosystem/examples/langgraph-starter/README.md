# LangGraph Starter

## Summary

This starter shows the smallest useful graph-shaped agent example in the repo:
plan, route, synthesize.

## Status

`starter`

## Why It Exists

Framework comparison pages are easier to extend when contributors can point to
small repo-owned examples instead of only to external demos. This starter keeps
the shape recognizable without turning the repo into a framework tutorial set.

## Related Handbook Pages

- [Agent Frameworks](../../agent-frameworks.md)
- [Ecosystem Overview](../../README.md)

## Folder Structure

```text
langgraph-starter/
├── README.md
├── SOURCE_NOTES.md
└── src/
    └── graph.py
```

## Quick Start

This project is a starter. Read `src/graph.py` for the minimal graph state and
node boundaries, then expand it into a fuller runnable example if needed.

## Constraints

- No framework dependency is wired.
- The graph is illustrative rather than executable.
- Tool adapters and model calls are placeholders.

## Next Steps

- Add a real runtime dependency.
- Add one tool node and one retry path.
