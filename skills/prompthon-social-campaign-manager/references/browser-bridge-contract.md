# Browser Bridge Contract

## Purpose

Use this reference when the skill needs to work with the live Local-mode browser page instead of only the production API.

This is the correct surface for:
- requesting a short handoff code from the open signed-in page
- requesting live `editor context`
- coordinating a local companion mutation that should also trigger visible page refresh

## Contract Snapshot

- protocol version: `social-manager-local-pack.v2`
- handoff request event: `prompthon:social-manager-local-handoff-request`
- handoff response event: `prompthon:social-manager-local-handoff-response`
- editor-context request event: `prompthon:social-manager-local-editor-context-request`
- editor-context response event: `prompthon:social-manager-local-editor-context-response`
- mutation request event: `prompthon:social-manager-local-mutation-request`
- mutation response event: `prompthon:social-manager-local-mutation-response`
- refresh event: `prompthon:social-manager-local-refresh`
- skill pack id: `prompthon-social-media-manager-local-pack.v2`

## Handoff Request Payload

```json
{
  "protocolVersion": "social-manager-local-pack.v2",
  "requestId": "<uuid>",
  "organizationId": "<org-id>",
  "agentId": "<agent-id>",
  "bridgeOrigin": "http://127.0.0.1:4319",
  "source": "codex_skill"
}
```

Expected response shape:

```json
{
  "protocolVersion": "social-manager-local-pack.v2",
  "requestId": "<uuid>",
  "source": "browser_page",
  "success": true,
  "code": "TLLMJW",
  "expiresAt": "<iso-timestamp>",
  "expectedBridgeOrigin": "http://127.0.0.1:4319"
}
```

The browser-page responder owns the handoff lookup and mint flow. In the
current rollout it should:
- prefer background retrieval through the signed-in page instead of requiring
  the operator to copy a visible short code
- when server-backed handoff reuse is enabled for that page, try
  `GET /api/agents/local-bridge/handoff/active` for the exact
  `organizationId + agentId + bridgeOrigin` tuple
- fall back to `POST /api/agents/local-bridge/handoff` when no active handoff
  exists
- return the resolved short code through the browser event response

Do not bypass this with direct terminal HTTP calls to the handoff retrieval
routes. Those routes depend on the signed-in page auth context.

## Editor-Context Request Payload

```json
{
  "protocolVersion": "social-manager-local-pack.v2",
  "requestId": "<uuid>",
  "organizationId": "<org-id>",
  "agentId": "<agent-id>",
  "source": "codex_skill"
}
```

Expected `context` payload:

```json
{
  "kind": "social_post_content_editor",
  "organizationId": "<org-id>",
  "agentId": "<agent-id>",
  "postId": "<post-id>",
  "title": "Post title",
  "content": "Current full content",
  "selection": {
    "field": "content",
    "start": 42,
    "end": 88,
    "selectedText": "old text",
    "prefixText": "previous context",
    "suffixText": "next context"
  }
}
```

## Browser-Side Snippet: Request Handoff

Use this only when direct page JavaScript execution is available. The page
should handle the background API retrieval or mint path internally. Ask the
user for the visible short code only when this event-based path is unavailable.

```js
async function requestPrompthonHandoff({ organizationId, agentId, bridgeOrigin = "http://127.0.0.1:4319" }) {
  return await new Promise((resolve) => {
    const requestId = crypto.randomUUID();
    const onResponse = (event) => {
      const detail = event?.detail;
      if (!detail || detail.requestId !== requestId) return;
      window.removeEventListener("prompthon:social-manager-local-handoff-response", onResponse);
      resolve(detail);
    };
    window.addEventListener("prompthon:social-manager-local-handoff-response", onResponse);
    window.dispatchEvent(
      new CustomEvent("prompthon:social-manager-local-handoff-request", {
        detail: {
          protocolVersion: "social-manager-local-pack.v2",
          requestId,
          organizationId,
          agentId,
          bridgeOrigin,
          source: "codex_skill",
        },
      })
    );
  });
}
```

## Browser-Side Snippet: Request Editor Context

```js
async function requestPrompthonEditorContext({ organizationId, agentId }) {
  return await new Promise((resolve) => {
    const requestId = crypto.randomUUID();
    const onResponse = (event) => {
      const detail = event?.detail;
      if (!detail || detail.requestId !== requestId) return;
      window.removeEventListener("prompthon:social-manager-local-editor-context-response", onResponse);
      resolve(detail);
    };
    window.addEventListener("prompthon:social-manager-local-editor-context-response", onResponse);
    window.dispatchEvent(
      new CustomEvent("prompthon:social-manager-local-editor-context-request", {
        detail: {
          protocolVersion: "social-manager-local-pack.v2",
          requestId,
          organizationId,
          agentId,
          source: "codex_skill",
        },
      })
    );
  });
}
```

## Usage Rules

- Prefer the in-page handoff event path over asking the user to copy the
  visible short code.
- Treat the visible short code from the Local-mode page header as a manual
  debug fallback.
- Prefer live `editor context` over stale cached post content when the user asks for highlighted-text edits.
- Persist content changes through the canonical social API after using browser context.
- Do not rely on browser-only DOM edits as the source of truth.
