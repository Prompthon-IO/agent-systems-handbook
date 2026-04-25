# Customer Support Email Agent Starter

## Summary

This starter turns the customer-support case study into a small local workflow:
read an inbound customer email, read a local support policy document, classify
the case, and draft a safe reply for human review.

The point is not helpdesk automation yet. The point is to make the support
agent's boundary inspectable before adding mailbox or CRM integrations.

## Status

`starter`

## Why It Exists

Customer support is a practical local-agent shape because the useful context is
often already nearby: an email export, a policy document, a refund rule, or an
FAQ file. This starter keeps that boundary visible by requiring explicit local
paths instead of pretending the agent knows the policy from memory.

## Related Lab Pages

- [Customer Support Agents](../../customer-support-agents.md)
- [Case Studies Overview](../../README.md)
- [Protocols And Interoperability](../../../systems/protocols-and-interoperability.md)

## Folder Structure

```text
customer-support-email-agent-starter/
├── README.md
├── SOURCE_NOTES.md
├── skill/
│   └── SKILL.md
└── src/
    ├── email_triage.py
    ├── policy_loader.py
    └── reply_guardrails.py
```

## Quick Start

This is a starter, not a finished helpdesk integration. The code sketch uses
only the Python standard library and focuses on the local-path boundary:

- customer message text in
- local policy file path in
- classified case plus draft reply out
- human-review flag out

Example:

```python
from reply_guardrails import draft_policy_grounded_reply

result = draft_policy_grounded_reply(
    email_text="Subject: Refund request\nI received the wrong item.",
    policy_path="/Users/example/support/refund-policy.md",
)

print(result.reply_subject)
print(result.reply_body)
print(result.needs_human_review)
```

For a repo-level smoke check, run `python3 scripts/verify_example_projects.py`
from the repository root.

## What To Inspect First

- Read `src/reply_guardrails.py` for the draft and review decision.
- Read `src/policy_loader.py` for how local policy evidence is extracted.
- Read `src/email_triage.py` for the intentionally small case classification.
- Read `skill/SKILL.md` for how the same workflow can be packaged as reusable
  instructions.

## Included Sample Files

- `skill/SKILL.md`: skill instructions for checking customer email and drafting
  policy-grounded replies from a local document path
- `src/email_triage.py`: lightweight classification and summary helpers
- `src/policy_loader.py`: local policy loading and evidence extraction helpers
- `src/reply_guardrails.py`: draft generation and human-review guardrails

## Constraints

- No mailbox, Gmail, CRM, or helpdesk adapter is implemented.
- The starter reads local text-like policy files only.
- Drafts are intended for human review, not automatic sending.
- Classification is keyword-based and intentionally small.
- The code does not claim to be a production support policy engine.

## Next Steps

- Add a mailbox adapter that writes inbound messages to explicit local paths.
- Add structured policy sections with stronger retrieval.
- Add evaluation fixtures for refunds, billing, complaints, and escalation.
- Add an audit artifact that records policy evidence and reviewer decision.
