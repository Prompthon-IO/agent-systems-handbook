# Social API Contract

## Purpose

Use this reference when the skill needs exact production route names, auth headers, attach-media payloads, rewrite payloads, or the `apply-plan` JSON shape.

This reference assumes zero repo access.
- Use the deployed API only.
- Use the bundled `scripts/manage_social_campaign.py` helper for automation.
- Do not depend on local Prompthon source files, local package scripts, or repo-relative assets.

## Production Base URL

Default production origin:

```text
https://agents.prompthon.io
```

All social-manager routes are organization-scoped:

```text
/api/organizations/:orgId/social/:path
```

Examples:
- `/api/organizations/<orgId>/social/channels`
- `/api/organizations/<orgId>/social/campaigns`
- `/api/organizations/<orgId>/social/posts`
- `/api/organizations/<orgId>/social/media/search`

## Auth Modes

### Protected production API token

Header:

```text
x-prompthon-local-bridge-token: <token>
```

Production bootstrap flow:
1. Open the signed-in Social Media Manager page in Local mode.
2. Prefer requesting a short handoff code through the browser-side handoff event so the signed-in page can resolve it in the background.
3. Fallback: use the short handoff code visible in the page header when the event path is unavailable.
4. Exchange the code:
   `POST /api/agents/local-bridge/exchange`
5. Use returned `access_token` in `x-prompthon-local-bridge-token`.

Important boundary:
- Do not call `GET /api/agents/local-bridge/handoff/active` or
  `POST /api/agents/local-bridge/handoff` directly from the terminal.
- Those are authenticated page-owned routes. The signed-in browser page must
  call them and then return the resolved short code through the browser event
  contract.

Example handoff exchange body:

```json
{
  "code": "TLLMJW",
  "bridgeOrigin": "http://127.0.0.1:4319"
}
```

### Local testing bypass

This remains available for non-production testing only. It is not the default for this skill.

Header:

```text
x-prompthon-local-auth-bypass: 1
```

Optional browser cookie for Clerk-reading client surfaces:

```text
prompthon_local_auth_bypass=1
```

## Route Map

### Read routes

- `GET channels`
- `GET campaigns`
- `GET posts`
- `GET posts/:postId`
- `GET account-settings/summary`
- `GET calendar`
- `GET analytics/summary`

### Campaign routes

- `POST campaigns`
- `PATCH campaigns/:campaignId`
- `DELETE campaigns/:campaignId`

### Media routes

- `POST media/search`
- `POST posts/:postId/media`

### Post routes

- `POST posts`
- `PATCH posts/:postId`
- `DELETE posts/:postId`
- `POST posts/:postId/variants`
- `POST posts/:postId/ai-rewrite`
- `POST posts/:postId/publish`
- `POST posts/:postId/schedule`

### Schedule routes

- `POST schedules/process`
- `POST schedules/:scheduleId/execute`
- `PATCH schedules/:scheduleId`
- `DELETE schedules/:scheduleId`

## Media Search Payload

Example:

```json
{
  "query": "new energy control room ai visualization",
  "limit": 12,
  "perProvider": 6,
  "orientation": "landscape",
  "providers": ["unsplash", "pexels"]
}
```

## Attach-Media Payload

Use this route for post media instead of trying to seed only `settings.media` during draft creation.

Accepted input patterns:
- `query` with provider search
- explicit `mediaUrls`
- explicit `candidates`
- `generatedMedia`

Example with search:

```json
{
  "query": "solar battery digital twin",
  "providers": ["unsplash", "pexels"],
  "maxImages": 1,
  "replaceExisting": true,
  "altText": "AI model monitoring a solar battery network"
}
```

Example with explicit remote URL:

```json
{
  "mediaUrls": [
    "https://images.example.com/solar-grid.jpg"
  ],
  "replaceExisting": true
}
```

Example with generated image payload:

```json
{
  "generatedMedia": {
    "title": "Generated social image",
    "contentType": "image/png",
    "base64": "<base64-png>"
  },
  "replaceExisting": true
}
```

Expected behavior:
1. prepare media candidates
2. upload or resolve the asset
3. update ordered post media attachments
4. update publish `settings.media`
5. return attached assets plus warnings and provider statuses

## Highlighted-Text Rewrite Payload

Use `POST posts/:postId/ai-rewrite` when the rewrite should remain AI-generated but scoped to selected text.

Example:

```json
{
  "tone": "clear",
  "selection": {
    "field": "content",
    "start": 42,
    "end": 88,
    "selectedText": "old text",
    "prefixText": "previous context",
    "suffixText": "next context"
  },
  "editorContext": {
    "kind": "social_post_content_editor",
    "organizationId": "<org-id>",
    "agentId": "<agent-id>",
    "postId": "<post-id>",
    "title": "Post title",
    "content": "Full live editor content"
  }
}
```

For deterministic replacement, compute the replacement from the captured editor context and then persist it with:
- `PATCH posts/:postId`
- body containing updated `rawIdea`

## Apply-Plan JSON

The helper CLI expects this shape:

```json
{
  "campaign": {
    "topic": "Generative AI + New Energy",
    "brief": "One-paragraph campaign instruction text.",
    "startAt": "2026-06-24T00:00:00-04:00",
    "endAt": "2026-07-01T00:00:00-04:00",
    "cadence": "One post per day at 9am from a different angle.",
    "status": "live",
    "channelConnectionIds": [
      "8f929418-daff-425f-866e-85aa7a4ed24e",
      "26012848-c43a-4b90-82b3-2aa2e7a4f3a1"
    ],
    "metadata": {
      "theme": "generative-ai-plus-new-energy"
    }
  },
  "posts": [
    {
      "title": "Grid intelligence angle",
      "copy": "Five to ten lines of richer social copy.",
      "publishAt": "2026-06-24T09:00:00-04:00",
      "providers": ["linkedin", "instagram"],
      "hashtags": ["GenerativeAI", "NewEnergy"],
      "metadata": {
        "mirroredCopy": true
      },
      "media": {
        "query": "smart grid ai dashboard",
        "providers": ["unsplash", "pexels"],
        "maxImages": 1,
        "replaceExisting": true
      }
    }
  ]
}
```

## Apply-Plan Behavior

For each plan:
1. create the campaign
2. create each post linked to that campaign
3. patch each post so final title, metadata, and provider variant overrides are explicit
4. attach media through `posts/:postId/media` when the post includes media input
5. schedule each post
6. return campaign id, post ids, schedule counts, attach counts, and warnings

## Drafting Defaults

When the user asks for substantial campaign content:
- write post copy as roughly 5 to 10 short lines
- keep the argument readable and specific
- use mirrored copy across providers when the user asks for the same content
- treat hashtags as supplemental
- do not leave media out by accident; either attach it or ask the user for media direction
