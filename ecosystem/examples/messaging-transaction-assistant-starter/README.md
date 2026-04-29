# Messaging Transaction Assistant Starter

This starter demonstrates a compact transaction flow inside a messaging-style
assistant. The motivating signal is WhatsApp prepaid recharge in India, but
the implementation is repo-native and generic: it teaches intent capture, plan
selection, user confirmation, and payment handoff boundaries without copying a
vendor UI.

## Status

`starter`

## What It Demonstrates

- capture a user's transaction intent from a chat message
- select a simple plan from local fixtures
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

## Boundaries

This starter does not process payments, store card data, call telecom APIs, or
send real messages. The assistant stops at a structured handoff that a real
payment surface would need to own.
