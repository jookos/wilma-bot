"""MCP tool definitions and handlers."""

from __future__ import annotations

import datetime
import json
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.types import TextContent, Tool

from wilma_bot.client import WilmaClient

# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="get_messages",
        description="Fetch the inbox message list from Wilma.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_schedule",
        description=(
            "Fetch the week schedule and school terms from Wilma. "
            "Returns parsed lesson events with teacher/room/time details."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": (
                        "ISO 8601 date (YYYY-MM-DD) for any day within the desired week. "
                        "Defaults to today if omitted."
                    ),
                }
            },
            "required": [],
        },
    ),
    Tool(
        name="get_notices",
        description="Fetch unread notices and announcements from Wilma.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

ToolHandler = Callable[[WilmaClient, dict[str, Any]], Awaitable[list[TextContent]]]


async def _get_messages(client: WilmaClient, _args: dict[str, Any]) -> list[TextContent]:
    messages = client.get_messages()
    return [TextContent(type="text", text=json.dumps(messages, ensure_ascii=False, indent=2))]


async def _get_schedule(client: WilmaClient, args: dict[str, Any]) -> list[TextContent]:
    date: datetime.date | None = None
    if raw_date := args.get("date"):
        date = datetime.date.fromisoformat(raw_date)

    schedule = client.get_schedule(date=date)

    # Serialise using Pydantic model_dump so datetime objects are converted
    payload = schedule.model_dump(mode="json")
    return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, indent=2))]


async def _get_notices(client: WilmaClient, _args: dict[str, Any]) -> list[TextContent]:
    notices = client.get_notices()
    return [TextContent(type="text", text=json.dumps(notices, ensure_ascii=False, indent=2))]


REGISTRY: dict[str, ToolHandler] = {
    "get_messages": _get_messages,
    "get_schedule": _get_schedule,
    "get_notices": _get_notices,
}
