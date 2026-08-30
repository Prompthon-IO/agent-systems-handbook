---
name: prompthon-social-campaign-manager
description: "Prepare channel-specific Prompthon social campaigns from a saved strategy and use guarded canonical Social operations when an isolated demo workspace is available. Use for course distribution drafts or explicitly requested production operation; keep strategy design separate and verify the deployed auth contract before any legacy production flow."
---

# Prompthon Social Campaign Manager

Own **Distribute** in Lesson 5. Read the [safety rules](references/safety-rules.md), [persistence contract](references/persistence-contract.md), and runnable [README](README.md) before the selected action.

## Workflow

1. Select the mode before opening a browser or making a request. Course/demo inputs use this workflow and `scripts/course_social.py`. Never run the legacy `apply-plan` command for a classroom exercise: it schedules as part of its flow. Explicit production work must first verify the deployed transport and authorization using [current source notes](references/canonical-host-contract.md); the preserved [production workflow](references/production-workflow.md) is a historical compatibility reference, not a promise that bridge-token auth still works.
2. Read the saved strategy from the same course workspace. Prepare a core idea, channel-specific copy, explicit provider IDs and offset-aware dates. Every post references a current strategy topic. The initial text-only course adapter supports LinkedIn/Facebook; media requests need a separate reviewed canonical media attachment workflow.
3. Generate and inspect an offline plan. It reuses the existing package's settings/variant helpers, records strategy id/revision, and creates only local preview plus skill-run metadata. It does not create canonical Social objects, schedules or messages.
4. For actual demo writes, use the authorized signed-in Host page in the in-app browser. Load `scripts/course_browser.js` as a reviewed helper without executing it automatically. Before writes it requires a live server-attested isolated demo workspace, simulation-only delivery policy, permitted channels/capabilities, current strategy revision and the exact reviewed plan hash. Missing backend capability is a blocker, not permission to use production channels or a local-auth bypass.
5. A draft requires explicit DRAFT approval. Schedule and publish simulation are additional actions requiring SCHEDULE or PUBLISH approval for the exact plan. All operations go through the current Host workspace operations endpoint to existing Social campaigns/posts; cookies stay in the browser. Never call the app's Host-signature endpoint directly or invent signing credentials.
6. Read back campaign, post copy/state, every target schedule/delivery and the course run. Draft, demo scheduled and demo simulated are distinct states; simulation is not public delivery. Recover canonical receipts after a partial/unknown response before any retry. Do not silently delete, reconnect a provider, promote a draft or send real social content from a course request.

## Shared boundary

Use course-support for local records or the explicitly configured Prompthon API. Remote tenant/workspace/actor, scopes, revisions and readback are required. Production backend deployment is separately tracked in [dependency #221](../course-support/references/backend-dependency.md). Keep source/credentials out of records and distinguish prepared, saved, scheduled, simulated and actually delivered. See [source notes](references/source-notes.md) for the original implementation and licensing boundary.
