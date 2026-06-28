---
name: prompthon-social-campaign-manager
description: Manage Prompthon Social Media Manager work against the deployed production app at agents.prompthon.io through the canonical organization-scoped social API. Use when Codex needs to open the production Social Media Manager in the in-app browser, guide a user through Local mode plus local companion setup, retrieve or mint a short handoff code through the signed-in browser page's background API path, exchange that handoff for a bridge token, inspect channel readiness, create or update social campaigns and posts, attach media through the API before scheduling, or rewrite highlighted post text from live editor context.
---

# Prompthon Social Campaign Manager

Use this skill for production Social Media Manager work that should go through the deployed Prompthon API and local companion bridge rather than manual post creation in the UI.

Browser requirement:
- The production Prompthon page must be opened and operated in the Codex in-app browser by default.
- Do not switch this workflow to Chrome or another external browser unless the user explicitly asks for that override.
- Treat the Codex in-app browser session as the source of truth for sign-in state, Local mode, handoff retrieval, and visible channel/editor context.

Assume the user has:
- the deployed app at `https://agents.prompthon.io`
- a signed-in browser session or the ability to sign in
- no local repo checkout

Assume this skill must remain runnable without any Prompthon codebase on disk.
- Do not require repo files, local app scripts, `pnpm`, or source checkout state.
- Use only the bundled skill resources plus the live deployed app, browser session, and local companion.
- Treat `scripts/manage_social_campaign.py` as the canonical automation entrypoint for bridge exchange and production social API operations.
- If a needed operation is not covered by the bundled script or the documented browser-event path, say so explicitly instead of assuming repo access.

Keep the canonical nouns straight:
- use `social campaign` for the planning record
- use `social post` for the parent draft and content record
- use `social publish target` for one post targeting one connected channel
- use `local companion` for the installed package on the user's machine
- use `localhost bridge` for the browser-to-local HTTP transport
- use `editor context` for the live open post editor content plus selection

## Quick Start

1. Open or reuse the production page in the Codex in-app browser.
- If the browser is already on an `agents.prompthon.io` Social Media Manager route, preserve the full URL.
- Otherwise open `https://agents.prompthon.io/en/home`.
- If browser control is available, do that immediately when the skill is invoked directly.
- Do not move this page to Chrome unless the user explicitly requests Chrome.

2. Resolve the active organization and agent from the open route.
- Reuse `orgId` and `agentId` from the visible page URL when present.
- Do not guess a different organization or agent.

3. Move the user onto the Social Media Manager Local-mode surface.
- Ask the user to switch the selected agent to Social Media Manager if needed.
- Ask the user to enable `Local` mode and keep that page open.
- Treat the visible compact handoff code in the rail header as an optional debug fallback, not the primary bridge-auth path.

4. Get bridge auth.
- Preferred: if browser execution is available and the page supports the local companion pack, request a handoff directly from the signed-in page using the event contract in `references/browser-bridge-contract.md`.
- The page-owned responder should resolve handoff in the background:
  - when server-backed handoff reuse is preferred, the page first tries `GET /api/agents/local-bridge/handoff/active` for the exact organization, agent, and bridge-origin tuple
  - if no active handoff exists, the page falls back to `POST /api/agents/local-bridge/handoff`
- Do not call `GET /api/agents/local-bridge/handoff/active` or `POST /api/agents/local-bridge/handoff` directly from the terminal or bundled CLI.
- Those routes require the signed-in browser page's auth context and are page-owned retrieval routes, not standalone CLI bootstrap endpoints.
- Fallback: ask the user for the short handoff code shown in the Local-mode page header when browser execution is unavailable or the event path cannot be used.
- Do not tell the user to open a repo or run app-internal scripts for handoff auth.
- Exchange the code with:

```bash
python3 "$PROMPTHON_SOCIAL_CAMPAIGN_MANAGER_HOME/scripts/manage_social_campaign.py" \
  exchange-handoff \
  --base-url "https://agents.prompthon.io" \
  --code "<short-code>"
```

- Save `access_token` as `PROMPTHON_SOCIAL_BRIDGE_TOKEN` and use `--auth-mode bridge-token`.

5. Inspect live production state before mutating anything.

```bash
python3 "$PROMPTHON_SOCIAL_CAMPAIGN_MANAGER_HOME/scripts/manage_social_campaign.py" \
  list-channels \
  --base-url "https://agents.prompthon.io" \
  --org-id "<org-id>" \
  --auth-mode bridge-token \
  --bridge-token "$PROMPTHON_SOCIAL_BRIDGE_TOKEN"
```

6. If channels are missing or disconnected, guide setup on the live page.
- Channel connection flows are browser-auth interactive.
- Use the in-app browser or Playwright only to inspect visible readiness, explain what the user should connect, and confirm the connected channel rows afterward.
- Do not fabricate connected channel ids or schedule real work against placeholder rows.

7. Create or update the campaign and posts through the API.
- Prefer `apply-plan` for a multi-post run.
- Always attach media through `POST posts/:postId/media` before scheduling when the post should carry media.
- Re-read campaigns or posts after mutations and report real readback, not write-only success.

## Production Workflow

### 1. Inspect channels, campaigns, and posts

Always start with:
- connected channels
- existing campaigns
- existing posts when the user might be updating, not creating

Useful commands:

```bash
python3 "$PROMPTHON_SOCIAL_CAMPAIGN_MANAGER_HOME/scripts/manage_social_campaign.py" \
  list-campaigns \
  --base-url "https://agents.prompthon.io" \
  --org-id "<org-id>" \
  --auth-mode bridge-token \
  --bridge-token "$PROMPTHON_SOCIAL_BRIDGE_TOKEN"

python3 "$PROMPTHON_SOCIAL_CAMPAIGN_MANAGER_HOME/scripts/manage_social_campaign.py" \
  list-posts \
  --base-url "https://agents.prompthon.io" \
  --org-id "<org-id>" \
  --auth-mode bridge-token \
  --bridge-token "$PROMPTHON_SOCIAL_BRIDGE_TOKEN"
```

### 2. Draft the campaign plan

Before writing:
- define the campaign topic and brief
- define the exact posting window
- choose the concrete connected channels
- prepare one scheduled timestamp per post
- prepare a media plan per post

When drafting content:
- keep the copy substantive, not just one-line slogans, unless the user asks for terse copy
- keep mirrored copy aligned across providers unless a provider-specific override is required
- treat hashtags as additive, not the main body

### 3. Create the campaign and posts

Use the helper CLI for either granular commands or one plan file.

Granular commands:
- `create-campaign`
- `create-post`
- `update-post`
- `schedule-post`

Plan command:
- `apply-plan`

The `apply-plan` flow does this in order:
1. create the `social campaign`
2. create each `social post`
3. patch each post so final copy and provider overrides are explicit
4. attach media through the media attach API when media input is present
5. schedule each post

### 4. Media rule

When a drafted post should include media:
- do not rely on raw `settings.media` in the initial draft payload
- always attach media through `POST /api/organizations/:orgId/social/posts/:postId/media`
- use one of:
  - `query` plus provider search
  - explicit `mediaUrls`
  - explicit `candidates`
  - `generatedMedia`

Examples:

```bash
python3 "$PROMPTHON_SOCIAL_CAMPAIGN_MANAGER_HOME/scripts/manage_social_campaign.py" \
  search-media \
  --base-url "https://agents.prompthon.io" \
  --org-id "<org-id>" \
  --auth-mode bridge-token \
  --bridge-token "$PROMPTHON_SOCIAL_BRIDGE_TOKEN" \
  --query "new energy control room ai visualization" \
  --providers unsplash pexels

python3 "$PROMPTHON_SOCIAL_CAMPAIGN_MANAGER_HOME/scripts/manage_social_campaign.py" \
  attach-media \
  --base-url "https://agents.prompthon.io" \
  --org-id "<org-id>" \
  --auth-mode bridge-token \
  --bridge-token "$PROMPTHON_SOCIAL_BRIDGE_TOKEN" \
  --post-id "<post-id>" \
  --query "solar battery digital twin" \
  --providers unsplash pexels \
  --max-images 1 \
  --replace-existing
```

If the user wants media but gives no usable search phrase or asset input, stop and ask for it. Do not silently draft a media-less post.

### 5. Highlighted-text editing

When the user wants to edit only highlighted text in the open post editor:
1. Prefer live `editor context` from the Local-mode page.
2. If browser execution is available, request editor context from the page using `references/browser-bridge-contract.md`.
3. Use one of two persistence paths:
- AI rewrite path:
  - `rewrite-post` with `selection` and `editorContext`
- Deterministic replacement path:
  - `replace-selection` with the captured editor-context JSON plus the exact replacement text
4. Persist the result through the social API, not browser-only text edits.

Examples:

```bash
python3 "$PROMPTHON_SOCIAL_CAMPAIGN_MANAGER_HOME/scripts/manage_social_campaign.py" \
  rewrite-post \
  --base-url "https://agents.prompthon.io" \
  --org-id "<org-id>" \
  --auth-mode bridge-token \
  --bridge-token "$PROMPTHON_SOCIAL_BRIDGE_TOKEN" \
  --post-id "<post-id>" \
  --tone "clear" \
  --selection-file /absolute/path/to/selection.json \
  --editor-context-file /absolute/path/to/editor-context.json

python3 "$PROMPTHON_SOCIAL_CAMPAIGN_MANAGER_HOME/scripts/manage_social_campaign.py" \
  replace-selection \
  --base-url "https://agents.prompthon.io" \
  --org-id "<org-id>" \
  --auth-mode bridge-token \
  --bridge-token "$PROMPTHON_SOCIAL_BRIDGE_TOKEN" \
  --editor-context-file /absolute/path/to/editor-context.json \
  --replacement-text "Sharper replacement copy for the highlighted span."
```

If the selected text no longer matches the current post content, refresh editor context and try again instead of forcing the patch.

## Browser Guidance

Use browser or Playwright help only where the API cannot replace the interaction:
- sign-in
- enabling Local mode
- triggering the in-page handoff responder when background retrieval is needed
- visually confirming the short handoff code only when the background handoff path is unavailable
- checking which channels are connected
- walking the user through provider connection screens
- capturing live `editor context` from the open page when highlighted-text editing is needed

Avoid browser clicking for campaign creation, post drafting, scheduling, or media attachment when the canonical social API already covers the operation.

## Zero-Repo Rule

Follow this skill as if the machine has no Prompthon repository checkout.
- The bundled Python script and reference docs are the whole local tool surface.
- All remote state must come from the deployed API or the signed-in browser page.
- When giving instructions to another agent or to the user, do not mention repo paths, local source edits, or webapp package commands.

## Resources

### scripts/

- `scripts/manage_social_campaign.py`
  Purpose: production-first CLI for bridge token exchange, campaign CRUD, post CRUD, media search and attach, scheduling, AI rewrite, and deterministic selected-text replacement

### references/

- `references/api-contract.md`
  Purpose: production base URL, auth contract, route map, attach-media payloads, and plan-file shape
- `references/browser-bridge-contract.md`
  Purpose: Local-mode handoff, mutation, and editor-context event names plus browser-side snippets for background handoff retrieval and highlighted-text workflows

## Environment Defaults

Use these defaults in shell snippets:

```bash
export PROMPTHON_SOCIAL_CAMPAIGN_MANAGER_HOME="${PROMPTHON_SOCIAL_CAMPAIGN_MANAGER_HOME:-$HOME/.codex/skills/prompthon-social-campaign-manager}"
export PROMPTHON_SOCIAL_BASE_URL="${PROMPTHON_SOCIAL_BASE_URL:-https://agents.prompthon.io}"
export PROMPTHON_SOCIAL_ORG_ID="${PROMPTHON_SOCIAL_ORG_ID:-}"
export PROMPTHON_SOCIAL_AGENT_ID="${PROMPTHON_SOCIAL_AGENT_ID:-}"
export PROMPTHON_SOCIAL_BRIDGE_TOKEN="${PROMPTHON_SOCIAL_BRIDGE_TOKEN:-}"
```

Read `references/api-contract.md` before adding new automation around auth or unsupported routes. Read `references/browser-bridge-contract.md` before using browser events for Local-mode handoff or highlighted-text editing.
