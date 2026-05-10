---
name: prompt-cache-agent-harness
description: Plan and inspect prompt-cache behavior for long-running Claude agent loops. Use when a user wants to split stable tool, system, and history context into cacheable layers, compare captured cache metadata, estimate cost impact from supplied pricing inputs, or keep durable memory outside the cached prefix.
---

# Prompt Cache Agent Harness

For the student-facing explanation of why this package exists, read
`README.md` first. This file is the invocation contract for Codex.

## Overview

Use this skill when the user is designing or debugging a long-running Claude
agent workflow where prompt caching is supposed to help. The goal is not to
call the Anthropic API directly from the skill. The goal is to keep the harness
local and inspectable:

1. plan a stable prompt spine
2. keep tools, system instructions, and long-lived history in explicit layers
3. keep durable memory and user-specific recall outside the cached prefix
4. read captured run artifacts after the agent loop executes
5. produce a small report on cache reads, cache writes, latency, and optional
   token-cost estimates

## When To Use

Use this skill for requests such as:

- design a prompt-cache layout for a persistent Claude agent
- separate cacheable static context from dynamic memory or retrieval facts
- compare cache reads and writes across cold and warm Claude runs
- estimate input-cost changes from supplied Anthropic pricing values
- explain why a cached prefix is being invalidated

Do not use this skill to promise provider-side savings without run artifacts.
If usage metadata is missing, say that and limit the answer to prompt-layout
review.

## Prompt Layout Rules

Use a layered prompt spine:

- `tools`: stable tool manifest, schemas, and capability boundaries
- `system`: stable role, policies, and operating instructions
- `reference`: stable project or domain context that changes rarely
- `session-summary`: compressed prior state only when it is intended to stay
  stable for many turns
- `dynamic-memory`: retrieved memories, current task facts, and user-specific
  details that should not invalidate the cached prefix
- `turn-input`: the current user request and latest volatile state

Prefer cache breakpoints after stable layers, not after dynamic memory. When
the provider supports explicit cache controls, apply them only to stable
content that can be reused safely.

## Expected Run Artifact

The helper reads one or more JSON or JSONL artifacts with fields like:

```json
{
  "label": "warm-run",
  "latency_ms": 2800,
  "input_tokens": 18000,
  "cache_creation_input_tokens": 1200,
  "cache_read_input_tokens": 14500,
  "output_tokens": 900,
  "stable_layer_hash": "tools-system-reference-v1",
  "dynamic_memory_hash": "retrieval-42",
  "notes": ["user-specific recall was appended after the cache boundary"]
}
```

Useful aliases are accepted for common captured metadata:

- `prompt_tokens` for `input_tokens`
- `cached_tokens` for `cache_read_input_tokens`
- `cache_write_tokens` for `cache_creation_input_tokens`
- `prefix_hash` for `stable_layer_hash`

## Local State And Outputs

Keep raw run artifacts outside the repo by default:

```text
~/.codex/state/prompt-cache-agent-harness/
  inputs/
  reports/
```

Do not commit transcripts, API responses, secrets, or provider logs unless the
user explicitly curates a redacted example for publication.

## Commands

Preview the helper:

```bash
python3 scripts/prompt_cache_report.py --help
```

Generate a Markdown report without pricing:

```bash
python3 scripts/prompt_cache_report.py \
  --input ~/.codex/state/prompt-cache-agent-harness/inputs/run-pair.jsonl \
  --output ~/.codex/state/prompt-cache-agent-harness/reports/cache-report.md
```

Generate a report with user-supplied pricing values:

```bash
python3 scripts/prompt_cache_report.py \
  --input ~/.codex/state/prompt-cache-agent-harness/inputs/run-pair.jsonl \
  --base-input-usd-per-mtok 3.00 \
  --cache-write-usd-per-mtok 3.75 \
  --cache-hit-usd-per-mtok 0.30 \
  --output ~/.codex/state/prompt-cache-agent-harness/reports/cache-report.md
```

## Interpretation Rules

- Treat changes to `stable_layer_hash` as the strongest cache-break signal.
- Treat changes to `dynamic_memory_hash` as expected only when dynamic memory is
  placed after the cache boundary.
- High cache writes with low cache reads usually means the workflow is paying
  setup cost without warm reuse.
- Strong cache reads on the warm run indicate the stable prefix is being reused.
- Keep durable memory separate from prompt caching; durable memory decides what
  to recall, while prompt caching rewards exact reusable prompt prefixes.

## Safety Boundaries

- Do not store sensitive conversation history in the cached prefix by default.
- Do not ask the user to expose Anthropic API keys to generate a report.
- Do not persist cost or trace reports in the repo unless the user asks.
- Do not turn a prompt-cache harness into an uncontrolled autonomous agent
  runner.

## Response Pattern

When reporting back, include:

- which layers should be cacheable
- cold versus warm cache-read share
- cache-write tokens versus cache-read tokens
- whether the stable layer hash changed
- whether dynamic memory appears to be outside the cached prefix
- cost estimates only when pricing values were supplied
