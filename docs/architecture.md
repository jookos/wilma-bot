# Architecture

## Overview

Wilma Bot is a single Python process that:

1. Reads credentials from environment variables on startup.
2. Starts an MCP server on **stdio** (default) or as a **streamable-HTTP** server (`--http <port>`).
3. On each tool call, authenticates against the Wilma HTTP API (if not already), fetches the requested data, and returns it as JSON text.

There is no database and no persistent state beyond the in-memory `WilmaClient` instance held for the lifetime of the process.

### Stdio transport (default)

```
MCP client (Claude / agent)
        │  stdio (JSON-RPC)
        ▼
  wilma_bot.__main__          entry point
        │
        ▼
  wilma_bot.mcp.server        FastMCP server
        │
        ▼
  wilma_bot.client.WilmaClient   synchronous HTTP client
        │  requests.Session
        ▼
  Wilma school instance (HTTPS)
```

### HTTP transport (`--http <port>`)

```
MCP client (remote agent / curl)
        │  HTTP POST /mcp  (streamable-HTTP JSON-RPC)
        ▼
  uvicorn (embedded in FastMCP)
        │
        ▼
  wilma_bot.__main__          entry point
        │
        ▼
  wilma_bot.mcp.server        FastMCP server
        │
        ▼
  wilma_bot.client.WilmaClient   synchronous HTTP client
        │  requests.Session
        ▼
  Wilma school instance (HTTPS)
```

## Module guide

### `wilma_bot.config`

Reads all configuration from `WILMA_*` environment variables (or a `.env` file) using `pydantic-settings`. Exposes a module-level `settings` singleton consumed by `__main__`.

### `wilma_bot.__main__`

Entry point. Instantiates `WilmaClient` from `settings` and creates the FastMCP server. Parses a single CLI flag:

- No flags → `server.run()` (stdio, default)
- `--http <port>` → sets `server.settings.host = "0.0.0.0"` and `server.settings.port`, then calls `server.run(transport="streamable-http")` which starts a uvicorn process serving the MCP endpoint at `/mcp`.

This is the only place where `config` and `mcp` are wired together.

### `wilma_bot.mcp.server`

Creates a `FastMCP` instance and registers tool handlers directly via the `@app.tool()` decorator. FastMCP handles both `list_tools` and `call_tool` dispatch internally.

### `wilma_bot.mcp.tools`

Defines the public MCP interface:
- `TOOLS` — list of `mcp.types.Tool` objects with JSON Schema input definitions
- `REGISTRY` — `{name: async handler}` mapping
- Each handler calls the appropriate `WilmaClient` method and serialises the result to a `TextContent` JSON string.

### `wilma_bot.client.wilma` — `WilmaClient`

The core of the application. A stateful HTTP client that implements the Wilma protocol (see `docs/protocol.md`):

| Method | Description |
|---|---|
| `login()` | 3-step auth: SessionID → credentials POST → Wilma2SID cookie + account/roles |
| `logout()` | Invalidates the server session and clears local state |
| `set_role(role)` | Switches the active role slug (by slug string or primusId) |
| `get_messages()` | `GET {slug}/messages/list` |
| `get_schedule(date)` | `GET {slug}/schedule?date=…` (HTML + JSON repair) + terms |
| `get_notices()` | `GET {slug}/notices` |
| `list_servers()` | Class method — fetches the official Wilma server directory |

Session validity is checked before every data call via `_refresh()` (`GET {slug}/overview`). Expired sessions trigger automatic re-login.

### `wilma_bot.client.models`

Pydantic v2 models for all API responses and domain objects. The split between raw API models and domain models:

| Layer | Models |
|---|---|
| Raw API | `SessionInit`, `AccountInfo`, `AccountRole` — field names match the Wilma JSON exactly |
| Domain | `Account`, `Role`, `Schedule`, `ScheduleEvent`, `Term`, `Teacher`, `Room` — normalised, snake_case, typed |

### `wilma_bot.client.json_repair`

Port of the `openwilma.js` `jsonRepair` utility. The Wilma schedule endpoint returns an HTML page with a JavaScript variable containing malformed JSON (unquoted keys, unescaped colons). This module repairs it before `json.loads()`.

Key function: `extract_and_repair(html: str) -> str`

## Data flow: `get_schedule`

```
call_tool("get_schedule", {"date": "2024-09-02"})
  │
  ▼
tools._get_schedule(client, {"date": "2024-09-02"})
  │  date = datetime.date(2024, 9, 2)
  ▼
WilmaClient.get_schedule(date)
  ├─ _ensure_fresh() → GET {slug}/overview   (session check)
  ├─ GET {slug}/schedule?date=2.9.2024       (HTML response)
  │    extract_and_repair(html) → json.loads()
  │    _parse_events(raw_events) → list[ScheduleEvent]
  └─ GET {slug}/schedule/export/students/{id}/ → list[Term]
  │
  ▼
Schedule(events=[...], terms=[...])
  │  .model_dump(mode="json")
  ▼
TextContent(type="text", text=<JSON string>)
```

## Dependency summary

| Package | Role |
|---|---|
| `mcp[cli]` | MCP server framework, FastMCP, stdio and streamable-HTTP transports |
| `requests` | Synchronous HTTP client for Wilma API calls |
| `beautifulsoup4` | Available for HTML parsing (imported in client) |
| `pydantic` | Data models and validation |
| `pydantic-settings` | Environment variable configuration |
