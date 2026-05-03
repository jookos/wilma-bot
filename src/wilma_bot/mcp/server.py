"""MCP server wiring (FastMCP)."""

from __future__ import annotations

import datetime
import json
import logging
import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from wilma_bot.client import WilmaClient
from wilma_bot.client.models import RoleType

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

    def _resolve_slug(guardee_id: int | None) -> str | None:
        if guardee_id is None:
            return None
        match = next(
            (r for r in client.roles if r.id == guardee_id and r.type == RoleType.guardian),
            None,
        )
        if match is None:
            raise ValueError(
                f"No guardian role found with id={guardee_id!r}. "
                "Call get_guardees() to list valid guardee IDs."
            )
        return match.slug

    @app.tool()
    def get_guardees() -> list[dict[str, Any]]:
        """List all children this guardian account is guarding.

        Returns objects with ``id`` and ``name``. Pass ``id`` as ``guardee_id``
        to get_messages, get_notices, or get_schedule to fetch a specific child's data.
        """
        return [{"id": g.id, "name": g.name} for g in client.get_guardees()]

    @app.tool()
    def get_messages(since: str | None = None, until: str | None = None, guardee_id: int | None = None) -> dict:
        """Fetch the inbox message list from Wilma.

        Args:
            since: Only return messages at or after this date/time. Accepts ISO dates
                   ("2026-04-01"), ISO datetimes ("2026-04-01 08:00"), Unix timestamps,
                   or relative durations ("1h", "30m", "2 days", "1 month").
                   Defaults to 6 months ago if omitted.
            until: Only return messages at or before this date/time. Same formats as since.
        """
        result = client.get_messages(slug=_resolve_slug(guardee_id))

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

        print(f'Returning {len(filtered)} messages ({len(messages)} got)')
        if isinstance(result, dict):
            return {**result, "Messages": filtered}
        return filtered  # type: ignore[return-value]

    @app.tool()
    def get_message(message_id: int, guardee_id: int | None = None) -> dict:
        """Fetches the contents of a message by its id from Wilma.

        Args:
            message_id: The id of the message to fetch.
            guardee_id: If provided, fetch from this specific guardee's inbox.
                        Use get_guardees() to obtain valid IDs.
        """
        return client.get_message(message_id, slug=_resolve_slug(guardee_id))

    @app.tool()
    def get_schedule(date: str | None = None, guardee_id: int | None = None) -> dict:
        """Fetch the week schedule and school terms from Wilma.

        Returns parsed lesson events with teacher, room, and time details.

        Args:
            date: ISO 8601 date (YYYY-MM-DD) for any day within the desired week.
                  Defaults to today if omitted.
            guardee_id: If provided, fetch the schedule for this specific guardee.
                        Use get_guardees() to obtain valid IDs.
        """
        parsed_date = datetime.date.fromisoformat(date) if date else None
        schedule = client.get_schedule(date=parsed_date, slug=_resolve_slug(guardee_id))
        return schedule

    @app.tool()
    def get_notices(guardee_id: int | None = None) -> dict:
        """Fetch unread notices and announcements from Wilma.

        Args:
            guardee_id: If provided, fetch notices for this specific guardee.
                        Use get_guardees() to obtain valid IDs.
        """
        notices = client.get_notices(slug=_resolve_slug(guardee_id))
        return notices

    @app.tool()
    def get_notice(notice_id: int, guardee_id: int | None = None) -> dict:
        """Fetch the full content of a single notice by its id from Wilma.

        Args:
            notice_id: The id of the notice to fetch.
            guardee_id: If provided, fetch from this specific guardee's notices.
                        Use get_guardees() to obtain valid IDs.
        """
        return client.get_notice(notice_id, slug=_resolve_slug(guardee_id))

    return app
