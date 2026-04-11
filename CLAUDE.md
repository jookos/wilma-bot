# CLAUDE.md — Wilma Bot

## Project overview

Wilma Bot is a Visma Wilma HTTP client packaged as an MCP (Model Context Protocol) server. It authenticates against a school's Wilma instance and exposes inbox messages, week schedule, and notices as MCP tools consumable by AI agents.

The server supports two transports: **stdio** (default, for Claude Code / local MCP clients) and **streamable-HTTP** (`--http <port>`, for remote or networked MCP clients). There is no database and no persistent state beyond the in-memory `WilmaClient` held for the lifetime of the process.

## Repository layout

```
src/wilma_bot/
├── __init__.py          # package version
├── __main__.py          # entry point — stdio or HTTP MCP server (--http <port>)
├── config.py            # pydantic-settings — reads WILMA_* env vars / .env
├── client/
│   ├── __init__.py      # re-exports WilmaClient and all model/exception types
│   ├── wilma.py         # WilmaClient — full Wilma HTTP protocol implementation
│   ├── models.py        # Pydantic v2 models for all API responses and domain objects
│   └── json_repair.py   # port of openwilma.js jsonRepair — fixes malformed schedule JSON
└── mcp/
    ├── __init__.py
    ├── server.py        # MCP Server wiring (list_tools / call_tool handlers)
    └── tools.py         # tool schemas (TOOLS list) and async handler functions

tests/
├── test_client.py       # WilmaClient unit tests (mocked HTTP)
├── test_json_repair.py  # json_repair unit tests
└── test_tools.py        # MCP tool handler tests

docs/
├── architecture.md      # module guide
├── configuration.md     # env var reference
├── mcp-tools.md         # tool schemas and example outputs
└── protocol.md          # Wilma HTTP protocol reference (reverse-engineered)
```

## Common commands

```bash
# Install (including dev dependencies)
uv pip install -e ".[dev]"

# Run the MCP server (stdio)
wilma-bot
python -m wilma_bot

# Run as HTTP MCP server on port 8080
wilma-bot --http 8080

# Tests
pytest
pytest -v tests/test_client.py   # single file

# Lint / format
ruff check src
ruff format src

# Type check
mypy src

# Docker
make image                        # build image (jookos.org/wilma-bot:latest)
make image IMAGE=myrepo/wilma-bot TAG=v1.0.0
make run-image                    # docker run with .env on default port (6060)
```

## Testing the HTTP transport

`test-http.sh` is an interactive curl-based shell for exercising the streamable-HTTP MCP interface:

```bash
# Start the server in one terminal
wilma-bot --http 8080

# In another terminal
./test-http.sh 8080
```

The script initializes the MCP session (obtaining the `mcp-session-id`) and drops into a REPL:

```
wilma-bot> list      # tools/list
wilma-bot> messages  # get_messages
wilma-bot> schedule  # get_schedule
wilma-bot> notices   # get_notices
```

## Key design decisions

- **`src/` layout** — prevents accidental imports of un-installed package.
- **`pyproject.toml` only** — no `setup.py` or `requirements.txt`.
- **`pydantic-settings`** — all config from `WILMA_*` env vars; `.env` auto-loaded.
- **`requests` (sync)** — the Wilma HTTP client is synchronous; the MCP layer wraps calls with `asyncio.to_thread` if needed. MCP tool handlers are `async` but call the blocking client directly (acceptable for a single-user stdio server).
- **Dual transport** — stdio (default) for Claude Code / local clients; `--http <port>` enables FastMCP's streamable-HTTP transport (uvicorn, `/mcp` endpoint) for remote clients.
- **No mocks in json_repair tests** — the repair function is pure; tested end-to-end with real broken JSON strings.

## Adding a new MCP tool

1. Add the client method to `src/wilma_bot/client/wilma.py`.
2. Add a Pydantic model to `src/wilma_bot/client/models.py` if the response has structure worth preserving.
3. Add a `Tool` entry to `TOOLS` in `src/wilma_bot/mcp/tools.py`.
4. Add an async handler function and register it in `REGISTRY`.
5. Add tests in `tests/test_tools.py`.

## Authentication flow (summary)

The Wilma auth is a 3-step process — see `docs/protocol.md` for the full spec:

1. `GET /index_json` → `SessionID`
2. `POST /index_json` (form body with credentials + SessionID) → `Wilma2SID` cookie
3. `GET /api/v1/accounts/me` + `GET /api/v1/accounts/me/roles` → account and role list

The `Wilma2SID` cookie is stored in the `requests.Session` and sent automatically on every subsequent request. Sessions are validated before data calls via `GET {slug}/overview`; expired sessions trigger automatic re-login.

## Environment / credentials

Credentials are never logged. The `_password` attribute on `WilmaClient` is a private instance variable; it is not exposed through properties or `__repr__`.

For local development, copy `.env.example` to `.env` and fill in your values. `.env` is gitignored.
