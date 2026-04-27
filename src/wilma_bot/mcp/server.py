"""MCP server wiring (FastMCP)."""

from __future__ import annotations

import datetime
import json
import logging
import re

from mcp.server.fastmcp import FastMCP

from wilma_bot.client import WilmaClient

logger = logging.getLogger(__name__)

_RELATIVE_RE = re.compile(
    r"^(\d+)\s*(hours?|h|months?|minutes?|mins?|m|days?|d|weeks?|w)$",
    re.IGNORECASE,
)
_TIMESTAMP_FMT = "%Y-%m-%d %H:%M"


def _parse_flexible_datetime(value: str) -> datetime.datetime:
    """Parse a flexible date/time string into a naive datetime.

    Supports:
    - Relative durations: "1h", "30m", "2 days", "1 month", "3 weeks"
    - ISO date/datetime: "2026-04-14", "2026-04-14 10:50"
    - Unix timestamp (int or float as string)
    """
    value = value.strip()

    try:
        return datetime.datetime.utcfromtimestamp(float(value))
    except ValueError:
        pass

    m = _RELATIVE_RE.match(value)
    if m:
        amount = int(m.group(1))
        unit = m.group(2).lower()
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        if unit.startswith("mo"):
            return now - datetime.timedelta(days=30 * amount)
        if unit.startswith("m"):
            return now - datetime.timedelta(minutes=amount)
        if unit.startswith("h"):
            return now - datetime.timedelta(hours=amount)
        if unit.startswith("d"):
            return now - datetime.timedelta(days=amount)
        if unit.startswith("w"):
            return now - datetime.timedelta(weeks=amount)

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unrecognized date/time format: {value!r}")


def create_server(client: WilmaClient) -> FastMCP:
    """Instantiate and configure the FastMCP server."""
    app = FastMCP("wilma-bot")

    @app.tool()
    def get_messages(since: str | None = None, until: str | None = None) -> dict:
        """Fetch the inbox message list from Wilma.

        Args:
            since: Only return messages at or after this date/time. Accepts ISO dates
                   ("2026-04-01"), ISO datetimes ("2026-04-01 08:00"), Unix timestamps,
                   or relative durations ("1h", "30m", "2 days", "1 month").
                   Defaults to 6 months ago if omitted.
            until: Only return messages at or before this date/time. Same formats as since.
        """
        result = client.get_messages()

        since_dt = _parse_flexible_datetime(since) if since else datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - datetime.timedelta(days=180)
        until_dt = _parse_flexible_datetime(until) if until else None

        messages = result.get("Messages", []) if isinstance(result, dict) else result
        filtered = []
        for msg in messages:
            ts_str = msg.get("TimeStamp", "")
            try:
                ts = datetime.datetime.strptime(ts_str, _TIMESTAMP_FMT)
            except ValueError:
                filtered.append(msg)
                continue
            if since_dt and ts < since_dt:
                continue
            if until_dt and ts > until_dt:
                continue
            filtered.append(msg)

        if isinstance(result, dict):
            return {**result, "Messages": filtered}
        return filtered  # type: ignore[return-value]

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
    def get_notices() -> dict:
        """Fetch unread notices and announcements from Wilma."""
        notices = client.get_notices()
        return notices

    @app.tool()
    def get_notice(notice_id: int) -> dict:
        """Fetch the full content of a single notice by its id from Wilma."""
        notice = client.get_notice(notice_id)
        return notice

    return app
