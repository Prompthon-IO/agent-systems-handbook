# Prompt Cache Agent Harness

## Why This Skill Exists

Long-running agents often carry a lot of repeated context: tool manifests,
system instructions, project policy, prior summaries, and durable memory.
Prompt caching can make those loops cheaper and faster, but only when the
reused prefix stays stable.

This skill turns that concern into a small local workflow. It helps an operator
plan a cache-friendly prompt spine, inspect captured Claude usage metadata, and
produce a report that separates cache behavior from durable memory design.

## Who It Is For

This package is for practitioners and builders who are experimenting with
persistent Claude agents and want answers to practical questions:

- which parts of the prompt should stay stable?
- did the warm run actually read from cache?
- are cache writes dominating the cost?
- did dynamic memory invalidate the cached prefix?
- what should move before or after the cache boundary?

## End-To-End Workflow

1. Design the agent prompt as named layers.
2. Keep tools, system instructions, and stable reference context before the
   cache boundary.
3. Keep user-specific memory, retrieval snippets, and current-turn inputs after
   that boundary unless they are intentionally stable.
4. Run the agent loop and save redacted usage metadata outside the repo.
5. Feed the captured artifacts into `scripts/prompt_cache_report.py`.
6. Read the report before changing prompts, tools, or memory placement.

The package does not call Anthropic directly. That keeps secrets, raw
transcripts, and provider responses out of the public handbook.

## What The Helper Checks

The helper reads JSON or JSONL run artifacts and reports:

- regular input tokens
- cache-write tokens
- cache-read tokens
- total input tokens across those usage buckets
- output tokens
- latency
- cache-read share
- cache-write share
- optional input-cost estimate from supplied pricing values
- changes to `stable_layer_hash`
- changes to `dynamic_memory_hash`

## Minimal Artifact

```json
{
  "label": "warm-run",
  "latency_ms": 2800,
  "input_tokens": 2500,
  "cache_creation_input_tokens": 1200,
  "cache_read_input_tokens": 14500,
  "output_tokens": 900,
  "stable_layer_hash": "tools-system-reference-v1",
  "dynamic_memory_hash": "retrieval-42"
}
```

The token buckets match Anthropic usage metadata: regular input tokens,
cache-creation input tokens, and cache-read input tokens are separate billable
counts. The report calculates cache shares against the sum of those input-side
buckets.

## Example Command

```bash
python3 scripts/prompt_cache_report.py \
  --input ~/.codex/state/prompt-cache-agent-harness/inputs/run-pair.jsonl \
  --output ~/.codex/state/prompt-cache-agent-harness/reports/cache-report.md
```

Add pricing values only when you have current pricing from the provider:

```bash
python3 scripts/prompt_cache_report.py \
  --input ~/.codex/state/prompt-cache-agent-harness/inputs/run-pair.jsonl \
  --base-input-usd-per-mtok 3.00 \
  --cache-write-usd-per-mtok 3.75 \
  --cache-hit-usd-per-mtok 0.30
```

## How To Read It In The Handbook

This package is a Practitioner example of a local-first Codex skill:

- `SKILL.md` defines when Codex should invoke it
- `scripts/prompt_cache_report.py` provides deterministic report generation
- `references/source-notes.md` explains the first-party source boundary
- `agents/openai.yaml` provides display metadata for compatible runtimes

The learning outcome is the design boundary: prompt caching rewards stable
prefixes, while durable memory decides what should be recalled. A good agent
loop needs both ideas, but they should not be collapsed into one hidden history
blob.
