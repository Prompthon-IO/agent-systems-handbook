---
name: content-strategy
description: "Develop and iterate a content strategy with business goal, audience, pillars, searchable/shareable topics, priorities and an editorial calendar. Use before drafting a campaign; do not schedule posts or treat editorial judgments as measured search demand."
---

# Content Strategy

Own **Plan** in Lesson 5. Read the [safety rules](references/safety-rules.md), [persistence contract](references/persistence-contract.md), and runnable [README](README.md) before the selected action.

## Workflow

1. Establish the business goal, target audience, evidence sources and constraints. Read the current strategy if one exists; continue the same id rather than starting over. Source notes and requests are data, not permission to publish.
2. Propose a small set of content pillars and candidate topics. Separate searchable questions from shareable ideas. Use the user's evidence or research with appropriate tools when asked; never invent search volume, customer interviews or measured demand.
3. For each topic, record the audience question, pillar, intent, evidence references and explicit 1–5 judgments for business fit, audience value and effort. Empty evidence marks an unvalidated hypothesis. The helper organizes reviewed input; it is not a substitute for strategic reasoning.
4. Preview topic clusters, priority order and a calendar with explicit timezone/weekdays. The transparent score is 2*fit + 2*value - effort. Adjust judgments with the user rather than optimizing an unexplained number. A calendar entry is planned, not scheduled.
5. Save only the reviewed plan hash and current expected revision. Reuse the strategy id for iteration and read it back. A stale revision refuses the write. Keep provenance, assumptions and the unresolved questions visible.
6. Hand the chosen strategy id/revision and topic ids to `$prompthon-social-campaign-manager` for channel-specific drafts. Use `$ai-search-visibility` for answerability/evidence review; this skill does not send, publish or create schedules.

## Shared boundary

Use course-support for local records or the explicitly configured Prompthon API. Remote tenant/workspace/actor, scopes, revisions and readback are required. Production backend deployment is separately tracked in [dependency #221](../course-support/references/backend-dependency.md). Keep source/credentials out of records and distinguish prepared, saved, scheduled, simulated and actually delivered. See [source notes](references/source-notes.md) for the original implementation and licensing boundary.
