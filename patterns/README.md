# Patterns

This lane captures reusable design patterns that show up across agent
implementations, independent of framework choice.

## What belongs here

- Tool use
- Planning and task decomposition
- Reflection and repair loops
- Short-term and long-term memory patterns
- Subagents and delegation
- Browser and computer-use patterns
- Human-in-the-loop workflows
- Long-running task design
- Deep research patterns

## Editorial intent

Pages in this lane should explain mechanism, tradeoffs, and failure modes.
They should stay useful even as individual frameworks rise or fall.

## Current pages

- [Agent Memory And Retrieval](./agent-memory-and-retrieval.md): how agents
  separate active state, durable memory, retrieval, and explicit artifacts.
- [Reasoning And Control Patterns](./reasoning-and-control-patterns.md): how
  think-act-observe loops shape control, explainability, and tool use.
- [Planning And Reflection](./planning-and-reflection.md): how plan-first and
  critique-and-refine patterns improve quality on longer tasks.
- [Agent Runtime Building Blocks](./agent-runtime-building-blocks.md): the
  runtime components that show up beneath most frameworks and custom agents.
