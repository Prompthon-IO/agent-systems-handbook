# Sample Projects

This guide collects the current repo-owned starter projects in one public
surface.

## Current sample projects

| Lane | Project | Status | Focus |
| --- | --- | --- | --- |
| Patterns | [Agent Memory Retrieval Starter](../patterns/examples/agent-memory-retrieval-starter/README.md) | `starter` | active notes, working memory, retrieval inputs, and durable artifacts |
| Systems | [Weather MCP Server Starter](../systems/examples/weather-mcp-server-starter/README.md) | `starter` | request validation and protocol-facing tool boundaries |
| Ecosystem | [LangGraph Starter](../ecosystem/examples/langgraph-starter/README.md) | `starter` | a minimal graph-shaped plan, route, synthesize flow |
| Case Studies | [Deep Research Agent Starter](../case-studies/examples/deep-research-agent-starter/README.md) | `starter` | planning, evidence collection, and citation-aware synthesis |

## How to use these starters

- Start with the related lab page linked from each project README.
- Use [Environment Setup](./environment-setup.md) before running starter-code
  checks locally.
- Run `python3 scripts/verify_example_projects.py` from the repository root to
  smoke-test the current example code.

## Important boundary

These projects are public starter examples, not hidden internal drafts. They
are meant to clarify system shape, code boundaries, and extension points.

They are also intentionally incomplete:

- no sample project in the current repo claims to be a finished production app
- some examples validate core Python behavior without yet wiring a real
  framework, protocol transport, search adapter, or persistence layer
- each project README should say clearly whether the project is `starter`,
  `partial`, or `runnable`

## Where future projects belong

Future source projects should stay lane-local:

- `patterns/examples/`
- `systems/examples/`
- `ecosystem/examples/`
- `case-studies/examples/`
