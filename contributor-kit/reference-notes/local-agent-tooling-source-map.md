---
title: Local Agent Tooling Source Map
owner: Prompthon IO
updated: 2026-04-24
scope: local agent tooling, skills, roots, resources, and file-grounded workflows
status: draft
---

# Local Agent Tooling Source Map

## Summary

This note gathers official source inputs for contributors writing about local
agent systems: agents that work near a user's files, tools, project state, and
workflow instructions rather than operating only as a remote chat surface.

Use it when a draft needs to explain what "local" actually means. The durable
pattern is not the location of one model. It is the combination of:

- an execution environment or local tool boundary
- reusable skill or workflow packaging
- explicit filesystem or document scope
- resources that can be selected, searched, read, or refreshed
- permission rules that make the boundary understandable to users

## How To Use This Note

This is a source map, not a full article. Future contributors should use it to:

- define the boundary before describing the agent
- choose the right source for the claim they are making
- keep local files, selected resources, skills, and connectors separate
- add case-study examples that show what the agent may read, write, and review

## Why It Matters

Local-agent topics are becoming easy to overstate. A useful handbook treatment
should separate several concerns that are often mixed together:

- `runtime`: where commands, scripts, files, or containers run
- `skills`: how reusable task knowledge is packaged
- `roots`: which local filesystem areas a tool-facing server may see
- `resources`: which files, schemas, records, or application objects can be
  exposed as model context
- `connectors`: how local and remote services become callable tools

That split helps contributors write case studies and starter projects without
pretending that every integration is the same kind of agent capability.

| Term | Reader question | Common mistake |
| --- | --- | --- |
| `runtime` | Where does the work execute? | Treating all agent work as a chat reply |
| `skills` | What reusable task knowledge is packaged? | Hiding stale instructions inside one long prompt |
| `roots` | Which filesystem boundaries are in scope? | Saying "file access" without naming the boundary |
| `resources` | Which selected objects can become context? | Assuming every backend object is automatically available |
| `connectors` | Which systems can be called as tools? | Treating integration access as permission to use all data |

## Scope Notes

Included:

- official OpenAI source material on Responses API tools, file search, remote
  MCP support, and computer environments
- official MCP material on roots and resources
- official Claude Code material on local stdio servers, project/user scopes,
  and MCP resources

Excluded:

- third-party MCP server listings
- unofficial prompt-injection commentary
- vendor comparisons that do not change the handbook's local-agent mental
  model
- implementation details for a production email or CRM integration

## Source Map

- [OpenAI Responses API tools and remote MCP support](https://openai.com/index/new-tools-and-features-in-the-responses-api/):
  use this for claims about hosted tools, remote MCP support, file search, and
  long-running background work.
- [OpenAI computer environment for agents](https://openai.com/index/equip-responses-api-computer-environment/):
  use this for claims about execution environments, persistent files, shell
  access, compaction, and agent skills as runtime support.
- [MCP introduction](https://modelcontextprotocol.io/docs/getting-started/intro):
  use this for a stable, high-level explanation of MCP as a connection layer
  between AI applications and external systems.
- [MCP roots](https://modelcontextprotocol.io/specification/2025-06-18/client/roots):
  use this when the draft needs to explain local filesystem boundaries.
- [MCP resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources):
  use this when the draft needs to explain application-controlled context
  surfaces such as files, schemas, or application-specific objects.
- [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp):
  use this as a practical example of local stdio servers, project-scoped MCP
  configuration, plugin-provided servers, and resources in a coding-agent
  workflow.

## Synthesis

The strongest local-agent spine is a layered one:

1. The user or host application chooses an operating boundary.
2. Tools and servers expose capabilities inside that boundary.
3. Resources and roots describe which context can be read or selected.
4. Skills package repeatable task knowledge.
5. The agent produces an artifact or action that can be reviewed.

For handbook purposes, this is more useful than saying "the agent has access to
files." Local access should always be explained with the boundary attached:
which files, which server, which transport, which permission, and which
artifact.

The same discipline applies to skills and connectors. A skill can tell the
agent how to perform a task, but it should not be treated as current evidence.
A connector can expose a useful system, but it should not imply permission to
read or act on every object in that system.

## Case-Study Hooks

Good local-agent case studies should make the boundary visible:

- customer-support email agent: inbound message path plus local policy
  document path
- coding agent: repository root plus issue, test, and branch permissions
- operations agent: dashboard or database resource plus read-only query rules
- research agent: source folder plus citation artifact output

Each case should state what the agent may read, what it may write, and what
requires human review.

## Gaps And Follow-up

- Add a production-readiness note on local-agent security risks, especially
  prompt injection from untrusted files and connectors.
- Add a small matrix comparing direct local scripts, local stdio MCP servers,
  remote MCP servers, and platform-hosted tools.
- Expand the customer-support case study once the starter code includes a real
  mailbox or Gmail adapter.

## Update Log

- 2026-04-24: Refined the note for contributor comprehension with usage
  guidance, term boundaries, and clearer source-to-claim mapping.
- 2026-04-23: Added a contributor-facing source map for local agent tooling,
  skills, roots, resources, and file-grounded workflows.
