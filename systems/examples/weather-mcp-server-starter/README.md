# Weather MCP Server Starter

## Summary

This starter sketches a protocol-facing tool service that exposes a small,
stable weather interface for agent use.

## Status

`starter`

## Why It Exists

Protocol examples are easier to reason about when they focus on one tool
boundary. This starter keeps the scope to request validation, predictable tool
shapes, and response packaging.

## Related Handbook Pages

- [Protocols And Interoperability](../../protocols-and-interoperability.md)
- [Systems Overview](../../README.md)

## Folder Structure

```text
weather-mcp-server-starter/
├── README.md
├── SOURCE_NOTES.md
└── src/
    └── server.py
```

## Quick Start

This is a starter, not a finished server. The example file shows the interface
shape and handler boundary without bringing in a full protocol runtime.

## Constraints

- No transport layer is implemented.
- No real weather API integration is included.
- Authentication and permission rules are still placeholders.

## Next Steps

- Add a concrete transport surface.
- Add permission checks and request logging.
