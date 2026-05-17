# Messaging Transaction Assistant Starter

This starter demonstrates a compact transaction flow inside a messaging-style
assistant. The motivating signals are Meta's April 2026 prepaid-recharge flow
and the May 2026 `Business AI on WhatsApp` launch for Indian small businesses,
but the implementation is repo-native and generic: it teaches catalog-grounded
replies, intent capture, plan selection, user confirmation, human takeover, and
payment handoff boundaries without copying a vendor UI.

## Status

`starter`

## What It Demonstrates

- keep a small business context grounded in local profile, catalog, and support
  notes
- capture a user's transaction intent from a chat message
- select a simple plan from local fixtures
- keep human takeover available when the business wants to step in directly
- require explicit confirmation before payment handoff
- keep payment execution outside the assistant
- record the source lineage that inspired the starter

## Quick Start

Run the repository-level smoke check:

```bash
python3 scripts/verify_example_projects.py
```

Or inspect the starter directly:

```bash
python3 ecosystem/examples/messaging-transaction-assistant-starter/src/run_demo.py
```

The demo prints the business context sources that the assistant is allowed to
use before it proposes a payment handoff.

## Current Product Signal

Meta's current `Business AI on WhatsApp` launch makes one reusable lesson more
concrete: the business-side assistant should answer from a bounded business
profile, catalog, and support context, while leaving seller override and
payment execution outside the automation loop.

## Boundaries

This starter does not process payments, store card data, call telecom APIs, or
send real messages. It also does not imply a live WhatsApp Business Platform
integration. The assistant stops at a structured handoff that a real business
operator or payment surface would need to own.
