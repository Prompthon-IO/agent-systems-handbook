# Agent Memory Retrieval Starter

## Summary

This starter shows one clean way to separate active notes, working memory,
retrieval inputs, and durable artifacts in a small agent loop.

## Status

`starter`

## Why It Exists

Memory examples often collapse everything into one vague history object. This
starter is intentionally narrower: it highlights the boundary between what the
agent is currently holding, what it can retrieve, and what it should preserve
as an artifact.

## Related Handbook Pages

- [Agent Memory And Retrieval](../../agent-memory-and-retrieval.md)
- [Patterns Overview](../../README.md)

## Folder Structure

```text
agent-memory-retrieval-starter/
├── README.md
├── SOURCE_NOTES.md
└── src/
    └── memory_flow.py
```

## Quick Start

This is a starter, not a runnable application. Read `src/memory_flow.py` for
the minimal state shape and use it as a base for a fuller example later.

## Constraints

- No storage backend is wired yet.
- No embedding or vector-store integration is included.
- The example favors clear boundaries over completeness.

## Next Steps

- Add a simple persistence layer.
- Add an artifact promotion rule and a retrieval trace.
