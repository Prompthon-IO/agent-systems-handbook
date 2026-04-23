---
name: local-customer-email-reply
description: Review inbound customer email, ground the reply in a local policy or FAQ document, and draft a safe response for complaints and queries.
---

# Local Customer Email Reply

Use this skill when a user wants an agent to review customer email and draft a
response based on a local document path such as
`/Users/example/support-policy.md`.

## Required Inputs

- `EMAIL_PATH`: local `.txt`, `.md`, `.json`, or `.eml` file containing the
  inbound customer message
- `POLICY_PATH`: local `.md`, `.txt`, or other text-readable file containing
  support policy, FAQ, refund rules, or escalation guidance
- optional `DRAFT_PATH`: local path where the reply draft should be written

## Workflow

1. Read the inbound email from `EMAIL_PATH`.
2. Read the grounding document from `POLICY_PATH`.
3. Extract customer name, issue, requested outcome, order or account
   identifiers, urgency, and sentiment.
4. Classify the message as one of:
   - `complaint`
   - `query`
   - `refund_request`
   - `billing_issue`
   - `handoff_required`
5. Draft a reply grounded only in the local document.
6. If the requested action is not supported by the document, do not invent
   policy. Mark the case `handoff_required`.
7. Return:
   - `summary`
   - `classification`
   - `policy_evidence`
   - `reply_subject`
   - `reply_body`
   - `needs_human_review`

## Guardrails

- Never promise refunds, credits, replacements, or legal outcomes unless the
  local document explicitly allows them.
- Never expose internal notes or hidden reasoning.
- Keep the reply short, calm, and customer-facing.
- Escalate abusive, safety, chargeback, regulatory, privacy, or deletion cases
  for human review.
- Treat missing or weak policy evidence as a handoff case.
