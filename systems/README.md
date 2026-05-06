# Systems

This lane focuses on production-minded system concerns, which is one of the
main opportunities for this repository to stand apart from lighter agent
courses and cookbook repos.

## What belongs here

- Context engineering
- Protocol interoperability
- Evaluation
- Observability
- Reliability
- Safety and governance
- Deployment and operations

## Editorial intent

Pages in this lane should move beyond demos. The goal is to explain how agent
systems behave as real software systems with interfaces, traces, boundaries,
and operational tradeoffs.

## Current pages

- [Context Engineering](./context-engineering.mdx): how systems write, select,
  compress, and isolate context for reliable multi-step work.
- [Agent UI Protocols And Generative UI](./agent-ui-protocols-and-generative-ui.mdx):
  how AG-UI and A2UI separate user-facing interaction from tool and agent
  protocols.
- [Protocols And Interoperability](./protocols-and-interoperability.mdx): how
  tool access, agent collaboration, and network discovery fit together.
- [Evaluation And Observability](./evaluation-and-observability.mdx): how to
  measure capability and explain failures in production-minded agent systems.

## Example starters

- [Weather MCP Server Starter](./examples/weather-mcp-server-starter/index.mdx):
  a thin protocol-facing tool service sketch for future interop examples.
