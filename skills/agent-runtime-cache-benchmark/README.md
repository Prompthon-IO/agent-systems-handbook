# Agent Runtime Cache Benchmark

## Why This Skill Exists

This package is not a user-facing product feature. It is a small
Practitioner-facing workflow example for the handbook.

The problem it teaches is simple:

- an agent workflow ran once with a cold prompt path
- the same workflow ran again with a supposedly warm path
- the operator wants to know whether prompt caching actually helped
- if it did not help, the operator wants to know what probably changed

That is the gap this skill fills.

Instead of hand-waving about prompt caching, it turns the question into a local,
repeatable workflow with structured inputs and a deterministic report.

## Who It Is For

This skill is for students, contributors, and operators who are building or
debugging agent workflows.

It is most useful when someone is already collecting run metadata and wants to
answer questions like:

- why did the warm rerun stay slow?
- why did cached-token reuse drop?
- did the system prompt change?
- did the tool manifest change?
- did conversation history spoil the reusable prefix?

## End-to-End Workflow

The workflow is intentionally small:

1. Run an agent workflow once and save a structured artifact.
2. Run the same workflow again and save a second structured artifact.
3. Feed both artifacts into this skill's helper script.
4. Let the helper compare the stable fields and basic metrics.
5. Read the report and decide what to change in the prompt layout.

The expected learning outcome is not "use this exact script forever." The point
is to teach a clear operational pattern:

- stable prefix first
- dynamic inputs later
- separate prompt-caching concerns from durable memory concerns
- make cache debugging inspectable instead of guess-based

## What The Skill Actually Checks

The helper compares:

- latency
- prompt tokens
- cached tokens
- cached-token share
- `system_prompt_hash`
- `tool_manifest_hash`
- `history_hash`
- optional `prefix_hash`
- optional `prompt_cache_key`

If one of the structural hashes changed, the report flags that as a likely
cache-break reason.

If the warm run still shows strong cached-token reuse, the report says the
prompt spine looks stable enough to benefit from caching.

## What It Does Not Do

This package does not:

- call OpenAI or Anthropic directly
- inspect provider internals
- prove savings without the input metadata
- replace real production observability

It is a local analysis tool. It only works with the evidence already captured
in the two run artifacts.

## Minimal Example

Example input:

```json
{
  "label": "warm-rerun",
  "latency_ms": 2900,
  "prompt_tokens": 1840,
  "cached_tokens": 1536,
  "system_prompt_hash": "sys-v1",
  "tool_manifest_hash": "tools-v1",
  "history_hash": "hist-v1",
  "prefix_hash": "prefix-v1"
}
```

Example command:

```bash
python3 scripts/cache_benchmark.py \
  --cold-run /path/to/cold-run.json \
  --warm-run /path/to/warm-run.json \
  --output /path/to/cache-benchmark.md
```

Example outcome:

- warm run is faster
- warm run reused 80 percent of prompt tokens
- no structural cache-break field changed
- likely conclusion: the prefix stayed stable enough for caching

## How To Read It In The Handbook

Treat this package as a Practitioner example of a Codex-compatible workflow:

- `SKILL.md` explains when the skill should be invoked
- `scripts/cache_benchmark.py` shows the deterministic helper
- `references/provider-cache-notes.md` anchors the logic in first-party docs

If you are a student reading the repo, the main story is:

1. prompt caching is a real operator concern
2. the repo should show at least one concrete workflow for diagnosing it
3. this package is that workflow
