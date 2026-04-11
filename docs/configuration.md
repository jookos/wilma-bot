# Configuration

All configuration is read from environment variables at startup. Variables are prefixed with `WILMA_`. A `.env` file in the project root is loaded automatically if present.

## Variables

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `WILMA_BASE_URL` | string | `https://raseborg.inschool.fi` | No | Base URL of your school's Wilma instance. Must not have a trailing slash. |
| `WILMA_USERNAME` | string | — | Yes | Your Wilma login username. |
| `WILMA_PASSWORD` | string | — | Yes | Your Wilma login password. |
| `WILMA_SESSION_TIMEOUT` | integer | `30` | No | HTTP request timeout in seconds. |

## `.env` file

Copy `.env.example` and fill in your values:

```bash
cp .env.example .env
```

```ini
WILMA_BASE_URL=https://yourschool.inschool.fi
WILMA_USERNAME=your_username
WILMA_PASSWORD=your_password
WILMA_SESSION_TIMEOUT=30
```

`.env` is listed in `.gitignore` and will never be committed.

## Finding your school's base URL

The official list of Wilma instances is published at:

```
https://wilmahub.service.inschool.fi/wilmat
```

Each entry has a `url` field — use that as your `WILMA_BASE_URL`.

## MCP client configuration

### Stdio (Claude Code / local clients)

Pass credentials as environment variables in the server configuration:

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

### HTTP (remote / networked clients)

Start the server with `--http <port>` (credentials come from `.env` or environment):

```bash
wilma-bot --http 8080
```

The MCP endpoint is available at `http://<host>:<port>/mcp`. Configure a remote MCP client to point at that URL. The server binds to `0.0.0.0` so it is reachable from outside the container or host.

See `test-http.sh` for a curl-based interactive test client.

## Notes

- The password is stored as a private instance variable on `WilmaClient` and is never logged or exposed through public properties.
- If `WILMA_USERNAME` or `WILMA_PASSWORD` are missing the process exits immediately with a validation error.
