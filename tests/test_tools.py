"""Tests for MCP tool functions via the FastMCP server."""

import datetime
import json
from unittest.mock import MagicMock

import pytest

from wilma_bot.client.models import Schedule, ScheduleEvent, ScheduleEventDate, ScheduleEventDetails, Term
from wilma_bot.mcp.server import create_server


@pytest.fixture()
def mock_client() -> MagicMock:
    client = MagicMock()
    client.get_messages.return_value = [{"id": 1, "subject": "Hello"}]
    client.get_notices.return_value = [{"title": "Test notice"}]

    event = ScheduleEvent(
        id=1,
        date=ScheduleEventDate(
            start=datetime.datetime(2024, 1, 15, 8, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2024, 1, 15, 9, 0, tzinfo=datetime.timezone.utc),
            length_minutes=60,
        ),
        short_name="Math",
        name="Mathematics",
        color="#FF0000",
        details=ScheduleEventDetails(
            info="",
            notes=[],
            teachers=[],
            rooms=[],
            vvt="",
            creator=None,
            editor=None,
            visible=True,
        ),
    )
    term = Term(
        name="Autumn 2024",
        start_date=datetime.datetime(2024, 8, 12),
        end_date=datetime.datetime(2024, 12, 20),
    )
    client.get_schedule.return_value = Schedule(events=[event], terms=[term])
    return client


@pytest.fixture()
def tools(mock_client: MagicMock) -> dict:
    """Return a dict of {tool_name: fn} extracted from the FastMCP server."""
    app = create_server(mock_client)
    # FastMCP stores tools in ._tool_manager._tools
    return {name: t.fn for name, t in app._tool_manager._tools.items()}


def test_get_messages(tools: dict, mock_client: MagicMock) -> None:
    result = json.loads(tools["get_messages"]())
    assert result[0]["subject"] == "Hello"


def test_get_schedule_no_date(tools: dict, mock_client: MagicMock) -> None:
    result = json.loads(tools["get_schedule"]())
    assert result["events"][0]["short_name"] == "Math"
    mock_client.get_schedule.assert_called_once_with(date=None)


def test_get_schedule_with_date(tools: dict, mock_client: MagicMock) -> None:
    tools["get_schedule"](date="2024-01-15")
    mock_client.get_schedule.assert_called_once_with(date=datetime.date(2024, 1, 15))


def test_get_notices(tools: dict, mock_client: MagicMock) -> None:
    result = json.loads(tools["get_notices"]())
    assert result[0]["title"] == "Test notice"
