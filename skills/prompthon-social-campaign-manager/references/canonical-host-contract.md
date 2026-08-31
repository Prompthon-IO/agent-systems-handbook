# Canonical Host source contract

Source audit 2026-08-30: Prompthon Web App checkout HEAD `f58570af7cc5f6d75e62faed31743fefd48a1cac`; the files below were clean at inspection. This establishes source behavior only, not the deployed production release.

- `apps/social-media-manager-agent/src/ui/api.ts` maps logical `/api/organizations/:orgId/social/:path` requests into Host `operation.execute` with `social.http.read` or `social.http.write`.
- `apps/web/src/app/api/agent-applications/workspaces/[workspaceId]/operations/route.ts` accepts signed-in request-user auth and a strict body containing `operationId`, `input`, `idempotencyKey`, `organizationId`. It checks workspace/org and Host capability before dispatch.
- `apps/web/src/services/agent-applications/transportService.ts` resolves the application release, uses server-owned signing and stores idempotent operation receipts. Students must not call the app's signed endpoint or receive Host signing secrets.
- `apps/social-media-manager-agent/src/server/social/socialHttpOperation.ts` maps path/method to the existing canonical service. `socialCanonicalService.ts` owns campaign/post/variant/schedule/delivery/audit behavior and readback shapes.
- `apps/web/src/services/agent/localBridgeRequestAuth.ts` explicitly marks the former bridge request-auth helper deprecated and says product APIs use normal request-user auth. Do not assume the retained legacy bridge docs authorize a current production flow.

Browser request shape (same signed-in origin; cookies remain browser-owned):

```json
{
  "operationId": "social.http.read",
  "organizationId": "<actual-organization-uuid>",
  "idempotencyKey": "<fresh-read-key>",
  "input": {"organizationId": "<same-uuid>", "path": "channels", "method": "GET", "body": null}
}
```

POST this to `/api/agent-applications/workspaces/<actual-host-workspace-id>/operations`. The response must prove outer success, completed receipt with matching operation/key, and successful inner `data.status` / `data.body`. Mutations use stable keys; readbacks use fresh keys so receipt replay cannot masquerade as current state.

Canonical `settings.targetChannels` currently contains provider identifiers, despite the field name. Invalid identifiers can fall back to all connected providers. The course adapter supports explicit `linkedin`/`facebook`, verifies all connected channel identities against the server-attested demo set, and refuses any real channel. The server must independently enforce this policy.

Read campaign lists and individual posts after mutations. `getPost` returns rawIdea, campaignId, postState, variants, schedules and deliveries. Schedule evidence uses provider, scheduledAt and status; compare instants across timezone representations. A queued/scheduled item is not a delivered post. Course publish simulation requires per-provider `simulated` delivery records with no public URL; current source does not yet establish that demo worker capability.
