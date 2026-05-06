# Source Notes

This starter is repo-native. It uses public references as design input without
copying implementation code or long-form text.

## First-Party References

- Anthropic prompt caching:
  https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Anthropic pricing:
  https://platform.claude.com/docs/en/about-claude/pricing

These sources inform the concepts of cache writes, cache reads, stable prompt
prefixes, and provider pricing columns. The starter keeps pricing values as
caller-supplied inputs because provider prices can change.

## Community Signal

- Community prompt-cache harness discussion:
  https://www.reddit.com/r/artificial/comments/1syw5al/87_cost_savings_sub3s_latency_i_built_a_warmcache/

The Reddit post was used only as the issue's topic signal. No code, examples,
or prose from that post are copied into this starter.

## Attribution Boundary

The implementation is a small standard-library Python sketch created for this
handbook. It avoids SDK-specific APIs so readers can map the structure onto
their own runtime and source attribution stays clean.
