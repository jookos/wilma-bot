# wilma-bot stack

Docker Compose deployment and AI assistant skill for wilma-bot.

The wilma-bot MCP server exposes three tools to any connected AI client:
- **`get_messages`** — fetch the inbox
- **`get_schedule`** — fetch the week timetable
- **`get_notices`** — fetch unread announcements

The MCP endpoint is a [streamable-HTTP](https://modelcontextprotocol.io/docs/concepts/transports) transport at `/mcp`.

---

## 1. Start the server

### Prerequisites

Export your Wilma credentials in the shell (or add them to `~/.bashrc` / `~/.zshenv`):

```bash
export WILMA_BASE_URL=https://yourschool.inschool.fi   # defaults to raseborg.inschool.fi if omitted
export WILMA_USERNAME=your_username
export WILMA_PASSWORD=your_password
export WILMA_SESSION_TIMEOUT=30   # optional, default 30s
export MCP_PORT=8080               # optional, default 8080
```

### Start

```bash
cd stack/
docker compose up -d
```

The MCP endpoint is now reachable at:

```
http://localhost:8080/mcp
```

(Replace `8080` with your `MCP_PORT` if you changed it.)

### Stop

```bash
docker compose down
```

---

## 2. Configure the MCP server in Claude Code

Run once to register the server globally (available in all projects):

```bash
claude mcp add --transport http --scope global wilma http://localhost:8080/mcp
```

Or for the current project only (writes to `.claude/settings.json`):

```bash
claude mcp add --transport http wilma http://localhost:8080/mcp
```

**Manual alternative** — edit `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "wilma": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

Verify the tools are visible:

```bash
claude mcp list
```

---

## 3. Configure the MCP server in Claude Desktop (macOS)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "wilma": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

Restart Claude Desktop after saving. The wilma tools will appear in the tool panel.

---

## 4. Configure the MCP server in OpenClaw

In OpenClaw, add the wilma-bot as an MCP server pointing to:

```
http://localhost:8080/mcp
```

The exact steps depend on your OpenClaw version. Typically you either:
- Add it through the **Settings → MCP Servers** UI, or
- Edit `~/.openclaw/config.json` (or `~/.config/openclaw/config.json`) and add an entry under `mcpServers`

Consult the [OpenClaw documentation](https://github.com/openclaw/openclaw) for the current configuration format.

---

## 5. Install the wilmabot skill

The skill teaches the AI how to use the wilma tools: summarising messages, displaying the schedule, detecting new messages, and setting up background polling.

### Claude Code

```bash
mkdir -p ~/.claude/skills/wilmabot
cp stack/skills/wilmabot/SKILL.md ~/.claude/skills/wilmabot/SKILL.md
```

The skill is now available as `/wilmabot` in any Claude Code session:

```
/wilmabot                   # check messages, schedule, and notices
/wilmabot messages          # inbox only
/wilmabot schedule          # this week's timetable
/wilmabot notices           # announcements
/wilmabot today             # today's schedule
/wilmabot 2026-04-14        # schedule for the week of that date
```

You can also trigger the skill by just asking naturally — the word **"wilma"** is a key trigger:

```
are there anything new on wilma?
what does the wilma schedule look like this week?
any new messages from the school?
```

### OpenClaw

Copy the skill to OpenClaw's skills directory (adjust path to match your installation):

```bash
mkdir -p ~/.openclaw/skills/wilmabot
cp stack/skills/wilmabot/SKILL.md ~/.openclaw/workspace/skills/wilmabot/SKILL.md
```

---

## 6. Set up the background poller

The background poller checks for new messages on a schedule and alerts you only when something new arrives. The skill remembers the last message it showed you, so alerts are never repeated.

### State file

The skill stores the last-seen message ID in a state file:
- Claude Code: `~/.claude/wilma-state.json`
- OpenClaw: `~/.openclaw/wilma-state.json`
- Fallback: `~/wilma-state.json`

The file is created automatically on the first run. To reset (re-report all messages as new):

```bash
echo '{"last_seen_message_id": 0, "last_checked": ""}' > ~/.claude/wilma-state.json
```

### Claude Code — using `/schedule`

In a Claude Code session, run `/schedule` and provide:

| Field | Value |
|---|---|
| Prompt | `POLL /wilmabot messages` |
| Cron | `3 9,12,16 * * 1-5` |
| Recurring | yes |
| Durable | yes |

This fires at **9:03, 12:03, and 16:03 Monday–Friday** in local time. Durable tasks survive session restarts and are written to `~/.claude/scheduled_tasks.json`.

> Scheduled tasks expire after 7 days and need to be re-created. Claude Code will remind you.

### Any client — natural language

You can also just tell your AI assistant:

> Check for new Wilma messages at 9:03, 12:03, and 16:03 on school days (Monday–Friday). If there are new messages, alert me with the subject and sender.

The assistant will use the `/schedule` or equivalent mechanism available in your client to set this up, or ask you to confirm the schedule.
