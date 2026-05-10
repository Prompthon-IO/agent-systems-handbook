# Source Notes

This package is grounded in first-party provider documentation and keeps
imported material out of the handbook.

## Anthropic

- Official prompt-caching guide:
  https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Official pricing reference:
  https://platform.claude.com/docs/en/about-claude/pricing

The package uses those sources for the operational concepts of prompt-cache
writes, prompt-cache hits, cache-aware prompt structure, and pricing columns.
It does not copy provider examples or hardcode current prices.

## Repo Boundary

- Raw API calls, transcripts, and usage logs stay outside git by default.
- Pricing values are caller-supplied because provider pricing can change.
- The helper is deterministic and local; it reads captured artifacts and
  produces a report.
