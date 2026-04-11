# Wilma Bot

Wilma Bot is a [Visma Wilma](https://www.visma.fi/inschool/) client packaged as an [MCP](https://modelcontextprotocol.io/) server. It exposes your Wilma inbox, schedule, and notices as tools that any MCP-compatible AI agent (e.g. Claude) can call directly.

## Features

- Full Wilma authentication (3-step session flow, auto-refresh)
- Inbox messages, week schedule, and notices as MCP tools
- Schedule parsed into structured JSON — teachers, rooms, times, terms
- Multi-role support (student / teacher / guardian / …)
- Runs over stdio — zero infrastructure required

## Requirements

- Python 3.12+
- A Wilma account on any supported school instance
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd wilma-bot

# 2. Create a virtual environment and install
uv venv && uv pip install -e .

# 3. Configure credentials
cp .env.example .env
$EDITOR .env          # fill in WILMA_USERNAME and WILMA_PASSWORD

# 4. Run the MCP server
wilma-bot
# or: python -m wilma_bot
```

The server communicates over stdio and is ready to be wired into any MCP client.

## Configuration

All settings are read from environment variables (prefix `WILMA_`) or a `.env` file in the project root.

| Variable | Default | Description |
|---|---|---|
| `WILMA_BASE_URL` | `https://raseborg.inschool.fi` | Your school's Wilma base URL |
| `WILMA_USERNAME` | *(required)* | Wilma login username |
| `WILMA_PASSWORD` | *(required)* | Wilma login password |
| `WILMA_SESSION_TIMEOUT` | `30` | HTTP request timeout in seconds |

See [docs/configuration.md](docs/configuration.md) for details.

## MCP Tools

| Tool | Description |
|---|---|
| `get_messages` | Fetch the inbox message list |
| `get_schedule` | Fetch the week schedule and school terms (accepts optional `date`) |
| `get_notices` | Fetch unread notices and announcements |

See [docs/mcp-tools.md](docs/mcp-tools.md) for full schemas and example responses.

## Integrating with Claude Code

Add this to your Claude Code MCP config (`.claude/settings.json` or `~/.claude.json`):

```json
{
  "mcpServers": {
    "wilma": {
      "command": "wilma-bot",
      "env": {
        "WILMA_BASE_URL": "https://yourschool.inschool.fi",
        "WILMA_USERNAME": "your_username",
        "WILMA_PASSWORD": "your_password"
      }
    }
  }
}
```

## Development

```bash
uv pip install -e ".[dev]"
pytest              # run tests
ruff check src      # lint
mypy src            # type check
```

See [docs/architecture.md](docs/architecture.md) for a guide to the codebase.

## Documentation

| Document | Description |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Codebase structure and module guide |
| [docs/configuration.md](docs/configuration.md) | All configuration options |
| [docs/mcp-tools.md](docs/mcp-tools.md) | MCP tool reference |
| [docs/protocol.md](docs/protocol.md) | Wilma HTTP protocol reference |

## License

MIT
