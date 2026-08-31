# Web App dependency: classroom persistence and safe Social access

Tracking issue: [#221](https://github.com/Prompthon-IO/agent-systems-handbook/issues/221).

Owner: Prompthon Web App / Social Media Manager stream. Status: **requires implementation and production verification**. Handbook integration is intentionally independent of production deployment.

## Evidence reviewed on 2026-08-30

The current local Web App checkout has organization-scoped Social canonical entities and migrations in `apps/social-media-manager-agent/src/server/`. It does not expose a confirmed course workspace/persistence API. `apps/web/src/services/agent/localBridgeRequestAuth.ts` is explicitly deprecated and states that active product routes use normal request-user authentication; the legacy verifier is retained only for historical tests. The existing Handbook Social Skill's bridge-token examples therefore cannot be assumed to authenticate the current deployment.

This was a source inspection, not a probe of an authenticated production tenant. Exact public API behavior and DB/schema placement still require the owner to confirm them. No local database credential was read or copied for this work.

## Required implementation

1. Provision instructor-approved demo/course workspaces using existing Prompthon users and organization membership. Issue short-lived, revocable course capabilities through the current signed-in app; never distribute Neon credentials or reinstate retired bridge authentication.
2. Implement [contract v1](backend-contract.md) with server-side validation, tenant membership enforcement on every row, optimistic revisions, idempotency, rate limits and mandatory canonical readback.
3. Decide whether the course domain uses tables/schema in the existing application Neon database or an isolated course database. Put migrations, RLS/application enforcement and connection configuration in the backend repo. Record this decision; the Handbook cannot infer it from local SQLite.
4. Reuse existing Social campaign/post/variant/schedule/channel models and active auth. Provide a server-attested demo organization/channel view for the course wrapper; reject production channels even if a student edits a plan. No `social_campaigns_v2` or client database access.
5. Provide instructor setup/cleanup, a UI or authenticated API inspection view for run/artifact/domain readback, request ids and operational telemetry. Demo reset must not touch active runs or real business/Social data.
6. Supply the real course origin, scope onboarding and disposable staging credentials to instructors through approved secret channels. Test cross-student isolation and persistence across restart on Neon before enabling remote exercises.

## Release gate

Record the owning backend issue/PR, migration decision, deployment id, environment, sanitized scope/readback evidence and remaining limitations. Until those are verified, Handbook local exercises and contract tests are available, while production course persistence and server-backed social scheduling remain blocked dependencies. A placeholder URL, CLI success, mocked response or static SQL proposal is not release evidence.

## First-party platform references

The intended hosting split is documented by [Vercel Postgres integration guidance](https://vercel.com/docs/postgres) and [Neon's Vercel connection guide](https://neon.com/docs/guides/vercel-manual). They describe hosting/connection mechanisms, not the existence of Prompthon's course API.
