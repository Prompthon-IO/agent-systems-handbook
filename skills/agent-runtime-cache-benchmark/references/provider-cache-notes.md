# Provider Cache Notes

This reference keeps the public skill package grounded in first-party cache
guidance without copying provider documentation into the repo.

## OpenAI

- Official guide: [OpenAI prompt caching](https://platform.openai.com/docs/guides/prompt-caching)
- The main structural rule is exact prefix reuse: keep stable instructions and
  tool definitions at the beginning, move dynamic user-specific content later,
  and watch `cached_tokens` in usage metadata.
- OpenAI also documents `prompt_cache_key` as a routing aid when many requests
  share a long common prefix.

## Anthropic

- Official guide: [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- Anthropic frames prompt caching as reusing specific prompt prefixes to reduce
  processing time and cost for repeated workloads.
- The public lesson for this skill is the same: benchmark stable prefixes,
  treat tool or instruction changes as likely cache-break events, and keep
  runtime reports local unless the user explicitly exports them.

## Repo Boundary

- This skill package uses those official docs as source input, not as imported
  copy.
- The benchmark helper stays provider-agnostic and only reads user-supplied run
  artifacts.
