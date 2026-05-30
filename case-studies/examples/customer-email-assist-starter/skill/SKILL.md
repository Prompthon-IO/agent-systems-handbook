---
name: customer-email-assist
description: Review labeled Gmail customer-support threads with a minimal-token workflow. Use when Codex needs to synchronize Gmail into a local SQLite issue queue, apply deterministic cleanup and classification first, reserve model usage for JSON-only message understanding and draft-field generation, and support dashboard review, customer approval, and reply sending for a local single-operator support workflow.
---

# Customer Email Assist

Use this skill to operate the `customer-email-assist-starter` example with the
fewest model tokens possible.

## Required Runtime Inputs

For direct Gmail API sync:
- `CUSTOMER_EMAIL_ASSIST_GMAIL_LABEL`
- `CUSTOMER_EMAIL_ASSIST_POLICY_PATH`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- optional `CUSTOMER_EMAIL_ASSIST_DB_PATH`

For connector-assisted import:
- `CUSTOMER_EMAIL_ASSIST_POLICY_PATH`
- optional `CUSTOMER_EMAIL_ASSIST_DB_PATH`

## Hard Rule

Use model tokens only for:

1. understanding cleaned inbound customer email content
2. producing JSON fields for reply templates

Do not use model calls for Gmail fetching, HTML cleanup, quoted-history
removal, signature stripping, customer matching, SQLite writes, analytics,
filtering, pagination, or send-queue execution.

## Deterministic Commands

Resolve paths relative to this starter directory.

```bash
npm run setup-local
tsx scripts/customer-email-assist.ts apply-send-queue
tsx scripts/customer-email-assist.ts prepare-inbound-batch --out /tmp/prepared-inbound.json
tsx scripts/customer-email-assist.ts import-prepared-batch --input /tmp/prepared-inbound.json
tsx scripts/customer-email-assist.ts persist-understanding --input /tmp/understanding.json
tsx scripts/customer-email-assist.ts prepare-draft-batch --policy "$CUSTOMER_EMAIL_ASSIST_POLICY_PATH" --out /tmp/draft-batch.json
tsx scripts/customer-email-assist.ts render-save-drafts --input /tmp/draft-fields.json
```

## Workflow

1. Run `apply-send-queue` first.
   - If a human already replied in Gmail on an approved thread, the script marks
     the issue `resolved` and does not send again.
   - Otherwise it sends the approved rendered reply and resolves the issue.
2. Run `prepare-inbound-batch`.
   - This fetches only labeled Gmail threads.
   - It keeps at most four cleaned inbound items per batch.
   - It skips ignored customers.
   - Prefer `--out <file>` so the CLI returns only a tiny summary.
3. Use the model once for `understand`.
   - Read only the JSON batch output.
   - Return JSON only.
   - Fields per item:
     - `gmailThreadId`
     - `gmailLastInboundMessageId`
     - `customerEmail`
     - `customerName`
     - `subject`
     - `receivedAt`
     - `originalMessageText`
     - `classification`
     - `summary`
     - `urgency`
     - `actionSuggestion`
4. Save that JSON and run `persist-understanding --input <file>`.
5. Run `prepare-draft-batch --policy <file>`.
   - This retrieves only a few policy evidence lines per issue.
   - Prefer `--out <file>` so the CLI returns only a tiny summary.
6. Use the model once for `draft-fields`.
   - Read only the draft batch JSON.
   - Return JSON only.
   - Fields per item:
     - `issueId`
     - `classification`
     - `draftFields.customerName`
     - `draftFields.acknowledgement`
     - `draftFields.nextStep`
     - `draftFields.policyEvidence`
     - `draftFields.signoff`
7. Save that JSON and run `render-save-drafts --input <file>`.
8. In the dashboard, let the user edit the rendered draft, approve send, mark
   resolved, approve pending customers, ignore customers, or update customer
   descriptions.

## Connector-Assisted Import

When Gmail access is available through the Codex Gmail connector instead of local
Google OAuth variables:

1. Use a Gmail query such as `newer_than:1d -in:spam -in:trash -category:promotions`.
2. Read only the latest inbound customer-authored content per thread.
3. Build a prepared inbound JSON batch that matches `PreparedInboundItem[]`.
4. Run `tsx scripts/customer-email-assist.ts import-prepared-batch --input <file>`.
5. Open the dashboard against that SQLite database for local review and approval.

## Response Discipline

- Keep assistant narration short.
- When a command result is enough, return only the result and the next needed
  action.
- Prefer compact JSON over pretty-printed output for deterministic CLI steps.

## Guardrails

- Keep the model inputs short. Do not send full thread history.
- Do not send raw policy documents to the model; only send the selected policy
  evidence lines from `prepare-draft-batch`.
- Keep `handoff_required` cases out of auto-send flows unless the user
  explicitly edits and approves the final reply.
- Treat ignored customers as non-actionable in future sync runs.
