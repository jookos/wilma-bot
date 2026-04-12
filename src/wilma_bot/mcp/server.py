"""MCP server wiring (FastMCP)."""

from __future__ import annotations

import datetime
import json
import logging

from mcp.server.fastmcp import FastMCP

from wilma_bot.client import WilmaClient

logger = logging.getLogger(__name__)


def create_server(client: WilmaClient) -> FastMCP:
    """Instantiate and configure the FastMCP server."""
    app = FastMCP("wilma-bot")

    @app.tool()
    def get_messages() -> dict:
        """Fetch the inbox message list from Wilma."""
        messages = client.get_messages()
        return messages

    @app.tool()
    def get_message(message_id: int) -> dict:
        """Fetches the contents of a message by its id from Wilma."""
        messages = client.get_message(message_id)
        return messages

    @app.tool()
    def get_schedule(date: str | None = None) -> dict:
        """Fetch the week schedule and school terms from Wilma.

        Returns parsed lesson events with teacher, room, and time details.

        Args:
            date: ISO 8601 date (YYYY-MM-DD) for any day within the desired week.
                  Defaults to today if omitted.
        """
        parsed_date = datetime.date.fromisoformat(date) if date else None
        schedule = client.get_schedule(date=parsed_date)
        return schedule

    @app.tool()
    def get_notices() -> str:
        """Fetch unread notices and announcements from Wilma."""
        notices = client.get_notices()
        return json.dumps(notices, ensure_ascii=False, indent=2)

    return app
