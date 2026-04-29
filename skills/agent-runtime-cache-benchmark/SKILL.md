---
name: agent-runtime-cache-benchmark
description: Compare two structured agent-run artifacts to estimate cache efficiency, explain likely cache breaks, and produce a local benchmark report. Use when a user wants to understand whether a prompt layout, tool manifest, or history shape is helping or hurting prompt-cache reuse.
---

# Agent Runtime Cache Benchmark

For a student-facing explanation of why this package exists and how the
end-to-end workflow fits into the handbook, read `README.md` first. This file
is the invocation contract for Codex.

## Overview

Use this skill to compare a colder first run with a warmer rerun of the same
workflow. The goal is not to guess provider internals. It is to inspect the run
artifacts you already have and explain whether your prompt spine stayed stable
enough to benefit from prompt caching.

This skill is local-first and report-first:

1. collect or normalize two structured run artifacts
2. compare latency, prompt tokens, cached tokens, and stable hashes
3. explain likely cache breaks
4. write a small Markdown report for operator review

## When To Use

Use this skill when the user asks for tasks such as:

- compare a cold run and a warm rerun for the same agent workflow
- explain why cached tokens dropped between two agent runs
- estimate whether a prompt or tool layout is cache-friendly before automation
- separate prompt-cache behavior from durable memory or retrieval behavior

Do not use this skill to claim provider-side savings that are not supported by
the input artifacts. If the run metadata does not expose token or cache fields,
say that clearly and limit the report to structural stability checks.

## Expected Input Shape

The helper accepts two JSON files with small, explicit fields such as:

```json
{
  "label": "warm-rerun",
  "latency_ms": 2900,
  "prompt_tokens": 1840,
  "cached_tokens": 1536,
  "system_prompt_hash": "sys-v1",
  "tool_manifest_hash": "tools-v1",
  "history_hash": "history-v2",
  "notes": [
    "User-specific inputs were appended at the end."
  ]
}
```

Useful optional fields:

- `output_tokens`
- `prompt_cache_key`
- `prefix_hash`
- `notes`

## Local State And Outputs

Keep runtime artifacts outside git:

```text
~/.codex/state/agent-runtime-cache-benchmark/
  inputs/
  reports/
```

## Commands

Run the helper relative to this skill directory.

Preview the CLI:

```bash
python3 scripts/cache_benchmark.py --help
```

Generate a Markdown report:

```bash
python3 scripts/cache_benchmark.py \
  --cold-run /path/to/cold-run.json \
  --warm-run /path/to/warm-run.json \
  --output /path/to/cache-benchmark.md
```

Emit JSON instead:

```bash
python3 scripts/cache_benchmark.py \
  --cold-run /path/to/cold-run.json \
  --warm-run /path/to/warm-run.json \
  --format json
```

## Interpretation Rules

- Treat changes to `system_prompt_hash`, `tool_manifest_hash`, or `prefix_hash`
  as likely cache-break events.
- Treat changes to `history_hash` as a likely warm-path spoiler when the run is
  expected to reuse a long prefix.
- Keep durable memory or retrieval changes separate from cache analysis unless
  they directly altered the prompt prefix.
- Prefer appending variable user input at the end of the prompt spine when the
  provider's cache rules reward exact prefix stability.

## Safety Boundaries

- Do not require committing transcripts, logs, or API credentials.
- Keep reports local by default.
- Do not infer business-sensitive content from hashes or token counts alone.
- Do not blur prompt caching with durable memory design; they solve different
  problems.

## Response Pattern

When reporting back, include:

- cold vs warm latency
- cold vs warm cached-token share
- the most likely cache-break fields
- whether the prompt spine appears stable enough for reuse
- what to move earlier or later in the prompt if the user wants better hits
