# Source Project Guidelines

Use this guide for repo-owned example projects and starters.

## Where source projects belong

Source projects live only in lane-local example folders:

- `patterns/examples/`
- `systems/examples/`
- `ecosystem/examples/`
- `case-studies/examples/`

Do not create `examples/` under `foundations/` in v1.

## Project naming

- Use lowercase kebab-case for the project slug.
- Name by topic and behavior, not by contributor name.

Examples:

- `agent-memory-retrieval-starter`
- `weather-mcp-server-starter`
- `langgraph-starter`
- `deep-research-agent-starter`

## Required folder shape

Start from [Source Project Template](./templates/source-project-template/).

Every project must include:

- `README.md`
- `SOURCE_NOTES.md`

Optional additions when relevant:

- `src/`
- `assets/`
- dependency manifests
- notebooks or config files

## Required project status

Each project README must declare one status:

- `starter`
- `partial`
- `runnable`

Use `starter` unless the project is meaningfully complete and documented.

## Working rules

- Keep the project linked to the handbook. Every starter should point back to a
  related page or lane README.
- Keep external-source influence visible in `SOURCE_NOTES.md`.
- Do not copy upstream README text or large code blocks.
- Only add runtime files that are directly relevant to the example.
- If the project is not runnable yet, say so clearly.

## Completion standard

A source project is ready for review when it:

- sits in the correct lane-local folder
- uses the required files
- declares status clearly
- explains what it demonstrates
- documents source lineage and repo-native adaptation
