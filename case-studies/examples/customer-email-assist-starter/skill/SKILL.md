---
name: customer-email-assist
description: Review Gmail customer-support threads with a minimal-token, connector-first workflow. Use when Codex needs to read Gmail through the Codex Gmail connector, import cleaned messages into a local SQLite issue queue, apply deterministic cleanup and classification first, reserve model usage for JSON-only message understanding and draft-field generation, and support dashboard review, customer approval, and queued reply handling for a local single-operator support workflow.
---

# Customer Email Assist

Use this skill to operate the `customer-email-assist-starter` example with the
fewest model tokens possible.

## Required Runtime Inputs

For the default connector-assisted workflow:
- `CUSTOMER_EMAIL_ASSIST_POLICY_PATH`
- optional `CUSTOMER_EMAIL_ASSIST_DB_PATH`

Gmail authentication should happen through the Codex Gmail connector. Do not ask
the user to configure local Google OAuth variables for the normal workflow.

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
tsx scripts/customer-email-assist.ts import-prepared-batch --input /tmp/prepared-inbound.json
tsx scripts/customer-email-assist.ts persist-understanding --input /tmp/understanding.json
tsx scripts/customer-email-assist.ts prepare-draft-batch --policy "$CUSTOMER_EMAIL_ASSIST_POLICY_PATH" --out /tmp/draft-batch.json
tsx scripts/customer-email-assist.ts render-save-drafts --input /tmp/draft-fields.json
```

## Workflow

1. Use the Codex Gmail connector to search the mailbox.
   - Prefer a narrow query such as `newer_than:1d -in:spam -in:trash -category:promotions`.
   - Read only shortlisted customer-authored messages.
   - Keep at most four cleaned inbound items per batch.
2. Build `/tmp/prepared-inbound.json` as `PreparedInboundItem[]`.
   - Include only `gmailThreadId`, `gmailLastInboundMessageId`, `subject`,
     `cleanBody`, `receivedAt`, and the customer fields.
   - Skip ignored customers when the local database already knows them.
3. Run `import-prepared-batch --input <file>`.
   - This writes the SQLite issue rows and renders deterministic fallback drafts
     without using local Gmail OAuth.
4. Use the model only if hard logic is not enough for `understand`.
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
5. Save model output, when used, and run `persist-understanding --input <file>`.
6. Run `prepare-draft-batch --policy <file>`.
   - This retrieves only a few policy evidence lines per issue.
   - Prefer `--out <file>` so the CLI returns only a tiny summary.
7. Use the model only if fallback templates are not enough for `draft-fields`.
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
8. Save that JSON and run `render-save-drafts --input <file>`.
9. In the dashboard, let the user edit the rendered draft, queue send, mark
   resolved, approve pending customers, ignore customers, or update customer
   descriptions.
10. For queued sends, use the Codex Gmail connector to create or send the reply
    from approved SQLite rows, then mark the issue resolved.

## Advanced Local OAuth Adapter

The repository still contains a direct Gmail API adapter for teams that
explicitly want a standalone local integration. Treat it as advanced and do not
present it as the normal setup path.

Required advanced variables:
- `CUSTOMER_EMAIL_ASSIST_GMAIL_LABEL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- `CUSTOMER_EMAIL_ASSIST_OPERATOR_EMAIL`

Advanced commands:

```bash
npm run sync:oauth
tsx scripts/customer-email-assist.ts prepare-inbound-batch --out /tmp/prepared-inbound.json
tsx scripts/customer-email-assist.ts apply-send-queue
```

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
