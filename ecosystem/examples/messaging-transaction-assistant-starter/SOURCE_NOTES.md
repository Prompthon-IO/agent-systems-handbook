# Source Notes

## Primary Signals

- Meta, "Bringing Prepaid Mobile Recharges to WhatsApp Users in India",
  April 29, 2026:
  https://about.fb.com/news/2026/04/bringing-prepaid-mobile-recharges-to-whatsapp-users-in-india/
- Meta, "Introducing Business AI on WhatsApp for Small Businesses in India",
  May 2026:
  https://about.fb.com/news/2026/05/introducing-business-ai-on-whatsapp-for-small-businesses-in-india/
- Meta for Developers, "WhatsApp Flows":
  https://developers.facebook.com/docs/whatsapp/flows
- Meta for Developers, "WhatsApp Cloud API":
  https://developers.facebook.com/docs/whatsapp/cloud-api
- Meta sample repository, "whatsapp-api-examples":
  https://github.com/fbsamples/whatsapp-api-examples
- WhatsApp sample repository, "WhatsApp-Flows-Tools":
  https://github.com/WhatsApp/WhatsApp-Flows-Tools

## Repo-Native Interpretation

The April recharge flow gives the starter a concrete transaction shape: users
discover a task, choose a recipient, confirm an operator, select a plan, and
hand off payment only after review.

The May `Business AI on WhatsApp` launch broadens the durable lesson. A useful
business-side messaging assistant should answer from bounded business context
such as a profile, catalog, or support notes, recommend a next step, and keep
human takeover available when the seller wants to step in directly.

This starter does not copy WhatsApp UI or implement Meta-specific behavior. It
uses the source as a product-shape signal for a generic messaging-native
transaction assistant with catalog-grounded replies and explicit handoff
boundaries.

The documentation and sample repositories are most useful for contributors who
want to extend this starter toward structured messaging, Flows, or Cloud API
delivery without claiming that this repo already ships those integrations.

## Attribution Boundaries

- Do not copy source screenshots or UI text into the starter.
- Do not imply the repo starter integrates with WhatsApp, UPI, Jio, Airtel, or
  Vi.
- Keep the code small enough to teach assistant boundaries rather than payment
  operations or vendor setup.
