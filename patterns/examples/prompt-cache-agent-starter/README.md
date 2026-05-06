# Prompt Cache Agent Starter

This starter shows a minimal prompt-cache-aware agent loop without depending on
a provider SDK or a production observability stack.

It demonstrates three ideas:

- put stable tools, system instructions, and reference context first
- keep dynamic memory and current user input outside the cached prefix
- compare cold and warm run metadata for cache reads, cache writes, latency,
  and optional token-cost estimates

The code is intentionally small so builders can inspect the boundary before
adapting it to a real Claude or multi-provider runtime.

## Status

`starter`

## Files

- `index.mdx`: handbook-facing project guide
- `SOURCE_NOTES.md`: source lineage and attribution boundary
- `src/prompt_cache_agent_starter.py`: tiny prompt-layer and benchmark helpers
- `tests/test_prompt_cache_agent_starter.py`: executable smoke test

## Local Check

From the repository root:

```bash
python3 patterns/examples/prompt-cache-agent-starter/tests/test_prompt_cache_agent_starter.py
```

The repo-level smoke suite also covers this starter:

```bash
python3 scripts/verify_example_projects.py
```

## Boundaries

This starter does not call an API, store transcripts, or hardcode provider
prices. Treat it as a shape for designing and testing cache boundaries before
wiring a real runtime.
