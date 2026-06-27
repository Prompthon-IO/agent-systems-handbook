# Prompthon Social Campaign Manager

## Why This Skill Exists

This package is a Practitioner-facing workflow example for production social
operations.

It exists because "help me post this campaign" sounds simple in chat, but the
real workflow is not just copywriting. A production social operator needs:

- the signed-in browser page as the source of truth
- the correct Prompthon organization and agent context
- Local mode plus the local companion bridge
- channel-readiness checks before scheduling
- API-backed media attachment and post readback after mutations

The package demonstrates a better pattern:

- use the live production page for sign-in and handoff
- use a deterministic helper for repeatable API operations
- inspect live state before mutating anything
- attach media through the canonical route instead of hidden draft fields
- verify the created campaign and posts by reading them back

## Who It Is For

This skill is for students, contributors, and operators who want to understand
what a real Codex-compatible production workflow looks like when browser auth,
bridge tokens, and organization-scoped APIs all matter.

It is most useful for requests such as:

- inspect connected social channels in production
- create a scheduled campaign across multiple providers
- attach media to a draft before scheduling
- rewrite highlighted text from the live open editor context

## End-to-End Workflow

The workflow is intentionally split across two surfaces:

1. Open the signed-in `agents.prompthon.io` Social Media Manager page.
2. Switch to Local mode and keep the exact organization and agent context.
3. Request or reuse a short handoff code through the page-owned browser event.
4. Exchange that code for a bridge token.
5. Inspect channels, campaigns, and posts through the production social API.
6. Create or update campaigns and posts through the helper CLI.
7. Attach media through the dedicated media route before scheduling.
8. Read the resulting state back and report real production outcomes.

The main teaching point is that this is not a UI-clicking workflow. It is a
browser-auth plus API-execution workflow with explicit boundaries between the
signed-in page, the local companion bridge, and the canonical social API.

## What The Package Actually Does

The package currently demonstrates:

- bridge-token bootstrap from a short Local-mode handoff code
- organization-scoped reads for channels, campaigns, and posts
- campaign creation and update flows
- post creation, patching, and scheduling
- media search and media attachment through `posts/:postId/media`
- highlighted-selection rewrite and deterministic replacement using live editor
  context
- multi-post plan application through one JSON plan file

It uses:

- `SKILL.md` for the Codex invocation contract
- `agents/openai.yaml` for UI metadata
- `scripts/manage_social_campaign.py` for deterministic production API calls
- `references/api-contract.md` and `references/browser-bridge-contract.md` for
  route names, payloads, and browser-event details

## What It Does Not Do

This package does not:

- require a Prompthon repo checkout on disk
- treat Chrome as the default browser surface
- call page-owned handoff routes directly from the terminal
- fabricate connected channel IDs or placeholder production state
- rely on browser-only DOM edits as the persisted source of truth
- default to local auth bypass for production work

## How To Read It In The Handbook

Treat this package as a Practitioner example of a production agent workflow:

- `README.md` explains the human story and the operating model
- `SKILL.md` explains when Codex should invoke the package
- `scripts/manage_social_campaign.py` implements the deterministic helper
- `references/*.md` document the API and browser-bridge contracts

If you are a student reading the repo, the main lesson is:

1. production agent workflows often depend on exact live auth state
2. browser context and API execution should have clear boundaries
3. a good skill package makes those boundaries explicit and repeatable
