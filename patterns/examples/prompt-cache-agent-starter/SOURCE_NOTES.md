# Source Notes

This starter is repo-native. It uses public references as design input without
copying implementation code or long-form text.

## First-Party References

- Anthropic Agent SDK cost tracking:
  https://code.claude.com/docs/en/agent-sdk/cost-tracking
- Anthropic Usage and Cost API:
  https://platform.claude.com/docs/en/manage-claude/usage-cost-api
- Anthropic prompt caching:
  https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Anthropic pricing:
  https://platform.claude.com/docs/en/about-claude/pricing
- OpenAI prompt caching:
  https://developers.openai.com/api/docs/guides/prompt-caching
- OpenAI current model guidance:
  https://developers.openai.com/api/docs/guides/latest-model

These sources inform the concepts of cache writes, cache reads, stable prompt
prefixes, prompt-cache routing keys, authoritative usage reporting, and
provider pricing columns. The starter keeps pricing values as caller-supplied
inputs because provider prices and billing rules can change.

## Current Trend Signal

- Seven-day stored article signal for this handbook refresh:
  https://arstechnica.com/ai/2026/06/anthropic-pauses-token-based-billing-for-its-claude-agent-sdk/

This article was used only as the topic signal for the refresh. Current claims
in the handbook-facing page come from the first-party docs above.

## Attribution Boundary

The implementation is a small standard-library Python sketch created for this
handbook. It avoids SDK-specific APIs so readers can map the structure onto
their own runtime and source attribution stays clean.
