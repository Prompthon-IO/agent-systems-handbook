---
name: crm-operations
description: "Resolve and safely create/update demo CRM contacts, deals, activity notes and follow-up tasks with revision checks and an atomic audit trail. Use for business-object operations; do not clean spreadsheets, analyze business performance or send customer messages."
---

# CRM Operations

Own **Operate** in Lesson 4. Read [safety](references/safety-rules.md), [persistence](references/persistence-contract.md) and the runnable [README](README.md) before executing the selected workflow.

## Workflow

1. Confirm the authorized organization/workspace and server-attested demo environment. Do not use production CRM accounts. The helper uses Prompthon course collections and has no HubSpot-specific integration.
2. Resolve before writing: contact by normalized email or exact id; deal by contact+title or id; activity/task by id. Stop on ambiguity or duplicate identity. The classroom resolver refuses a collection at its 500-record bound instead of assuming a truncated list is complete.
3. Read the latest revision and referenced contact/deal. Validate email, finite nonnegative amount, explicit currency, ISO dates and allowed stages/statuses. Do not silently merge contacts, reassign another contact's deal or accept audit/system fields from input.
4. Preview `plan --request FILE`. Review before/after, entity id, revision, scope and returned approval hash. Apply only that reviewed plan using `--confirm SHA`; a concurrent change invalidates it. Each write includes audit evidence in the same atomic entity record.
5. A deal stage change or creation already marked won/lost requires additional action-time approval and `--approve-high-impact`. The ordinary patch approval is not that extra approval. Do not delete records, silently close deals or send a follow-up message because a task exists.
6. Read back the object and audit trail with `show`, and report actual state. An unchanged retry is reported unchanged. If a final run save fails after the entity write, inspect the canonical object/audit before retrying. Hand source preparation to Structure and performance questions to Analyze.

## Shared boundary

Use the course-support client for local or explicitly configured Prompthon storage. Remote organization/workspace, server-derived actor, scopes, revisions and canonical readback are mandatory. The Web App backend remains [a tracked dependency](../course-support/references/backend-dependency.md); never give learners a Neon connection string. See [source notes](references/source-notes.md) for licensing and the original implementation boundary.
