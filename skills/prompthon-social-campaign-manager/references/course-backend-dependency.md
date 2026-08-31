# Required demo backend capability — not yet provisioned

Tracked by [issue #221](https://github.com/Prompthon-IO/agent-systems-handbook/issues/221). The browser adapter is executable client code tested against a synthetic Host, but these course-specific endpoints and simulation policy are an explicit dependency. The existing canonical Social service does not become classroom-safe merely because a client sets a demo flag.

## Server contract

Under the common scoped course prefix, implement authenticated `GET /social-context?preparedRunId=...&planSha256=...`. Resolve the real actor and verify course membership, organization, workspace, prepared skill run and plan. Return `organization_id`, `workspace_id`, `application_id: prompthon.social-media-manager`, `host_workspace_id`, `environment: demo`, `isolated_demo: true`, `delivery_mode: simulation`, short-lived `expires_at`, permitted `social:draft|schedule|publish` capabilities and `channels[{id,provider,delivery_mode}]`.

These fields must derive from server-owned workspace/provider bindings, not caller JSON or a channel name. Bind the course workspace to its actual Host workspace and canonical Social organization. Require UUID organization ids where the Host contract does. Reject missing/stale capability, cross-tenant references and production channels before a write. The normal signed-in browser session must be supported; never export cookies or grant students Host signing/database secrets.

The common `GET /records/content_strategies/:id` must work for that authorized browser context so the adapter can verify current strategy revision. Student input must not bypass the server policy by calling the Host operation route directly: enforce course roles, allowed providers, operation scope and simulation delivery in the Host/app dispatch and background workers as well.

Reuse canonical campaigns/posts/variants/schedules/publish-targets/deliveries/audit. Add course strategy linkage to their existing metadata; do not create parallel social tables. Draft remains draft. Demo scheduling creates visible canonical schedule records but cannot reach external provider execution. Demo publish creates canonical per-provider delivery evidence with status simulated and no external post URL. Client-side checks or disabled UI buttons alone do not satisfy this requirement.

Implement authenticated `POST /social/record-receipts` with `prepared_run_id`, `plan_sha256`, `action`, `receipt_ids`. Look up actual Host receipts server-side, check actor/workspace/action/resource ownership, inspect canonical readbacks and append common `skill_runs` evidence. Do not trust arbitrary caller-supplied success snapshots. Return a run_id that the browser can GET and verify with matching scope, succeeded status and metadata.plan_sha256. Use idempotency and reconcile partial operations; do not blindly replay an uncertain external request.

## Browser use after deployment verification

Keep the real signed-in Host page open in the in-app browser. Confirm origin, organization and course workspace from live context. Load the reviewed `scripts/course_browser.js` without auto-running it, then call `PrompthonCourseSocial.execute(plan, {action: 'draft', planSha256: plan.plan_sha256, confirm: 'DRAFT'})` only after explicit draft authorization. Schedule/publish simulation needs separate SCHEDULE/PUBLISH authorization; the helper never infers it from a content plan.

The adapter refuses redirects, missing capabilities, stale strategies, wrong targets and mismatched readbacks. A partial result includes known ids/receipt ids and requires recovery before retry. Never use local-auth bypass, the historical bridge helper, real provider channels or a direct database connection to get around this dependency.

## Acceptance evidence

Use an isolated demo org with two synthetic providers, a course actor and a second forbidden org. Show successful canonical draft/readback, explicit scheduling approval, simulated worker output, blocked production/cross-org operations, unknown-provider refusal, expired capability, stale strategy, idempotent recovery and durable course run readback. Verify no external provider requests. Local Node tests exercise the client protocol only; they do not prove backend provisioning or a real schedule.
