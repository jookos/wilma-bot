"""Tests for MCP tool functions via the FastMCP server."""

import datetime
from unittest.mock import MagicMock

import pytest

from wilma_bot.client.models import (
    Guardee,
    Role,
    RoleType,
    Schedule,
    ScheduleEvent,
    ScheduleEventDate,
    ScheduleEventDetails,
    Term,
)
from wilma_bot.mcp.server import create_server


@pytest.fixture()
def mock_client() -> MagicMock:
    client = MagicMock()
    client.get_messages.return_value = [{"id": 1, "subject": "Hello"}]
    client.get_notices.return_value = [{"title": "Test notice"}]
    client.get_guardees.return_value = [
        Guardee(id=101, name="Alice"),
        Guardee(id=102, name="Bob"),
    ]
    client.roles = [
        Role(id=101, name="Alice", type=RoleType.guardian, is_default=True, slug="profiles/101", form_key="fk101"),
        Role(id=102, name="Bob", type=RoleType.guardian, is_default=False, slug="profiles/102", form_key="fk102"),
    ]

    event = ScheduleEvent(
        id=1,
        date=ScheduleEventDate(
            start=datetime.datetime(2024, 1, 15, 8, 0, tzinfo=datetime.UTC),
            end=datetime.datetime(2024, 1, 15, 9, 0, tzinfo=datetime.UTC),
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


SAMPLE_MESSAGES = {
    "Messages": [
        {"Id": 1, "Subject": "Old", "TimeStamp": "2026-03-01 10:00"},
        {"Id": 2, "Subject": "Mid", "TimeStamp": "2026-04-09 11:01"},
        {"Id": 3, "Subject": "New", "TimeStamp": "2026-04-14 10:50"},
    ]
}


def test_get_messages_default_since(tools: dict, mock_client: MagicMock) -> None:
    mock_client.get_messages.return_value = SAMPLE_MESSAGES
    result = tools["get_messages"]()
    # "Old" message from 2026-03-01 is within 6 months of test data; all three should pass
    assert len(result["Messages"]) == 3


def test_get_messages_default_since_excludes_old(tools: dict, mock_client: MagicMock) -> None:
    old_messages = {
        "Messages": [
            {"Id": 99, "Subject": "Ancient", "TimeStamp": "2020-01-01 00:00"},
            *SAMPLE_MESSAGES["Messages"],
        ]
    }
    mock_client.get_messages.return_value = old_messages
    result = tools["get_messages"]()
    assert all(m["Id"] != 99 for m in result["Messages"])


def test_get_messages_since(tools: dict, mock_client: MagicMock) -> None:
    mock_client.get_messages.return_value = SAMPLE_MESSAGES
    result = tools["get_messages"](since="2026-04-01")
    assert [m["Id"] for m in result["Messages"]] == [2, 3]


def test_get_messages_until(tools: dict, mock_client: MagicMock) -> None:
    mock_client.get_messages.return_value = SAMPLE_MESSAGES
    result = tools["get_messages"](until="2026-04-10 00:00")
    assert [m["Id"] for m in result["Messages"]] == [1, 2]


def test_get_messages_since_and_until(tools: dict, mock_client: MagicMock) -> None:
    mock_client.get_messages.return_value = SAMPLE_MESSAGES
    result = tools["get_messages"](since="2026-04-01", until="2026-04-10 00:00")
    assert [m["Id"] for m in result["Messages"]] == [2]


def test_get_schedule_no_date(tools: dict, mock_client: MagicMock) -> None:
    result = tools["get_schedule"]()
    assert result.events[0].short_name == "Math"
    mock_client.get_schedule.assert_called_once_with(date=None, slug=None)


def test_get_schedule_with_date(tools: dict, mock_client: MagicMock) -> None:
    tools["get_schedule"](date="2024-01-15")
    mock_client.get_schedule.assert_called_once_with(date=datetime.date(2024, 1, 15), slug=None)


def test_get_notices(tools: dict, mock_client: MagicMock) -> None:
    result = tools["get_notices"]()
    assert result[0]["title"] == "Test notice"


def test_get_guardees_returns_list(tools: dict, mock_client: MagicMock) -> None:
    result = tools["get_guardees"]()
    assert result == [{"id": 101, "name": "Alice"}, {"id": 102, "name": "Bob"}]
    mock_client.get_guardees.assert_called_once_with()


def test_get_guardees_empty(tools: dict, mock_client: MagicMock) -> None:
    mock_client.get_guardees.return_value = []
    result = tools["get_guardees"]()
    assert result == []


def test_get_messages_with_guardee_id(tools: dict, mock_client: MagicMock) -> None:
    mock_client.get_messages.return_value = SAMPLE_MESSAGES
    tools["get_messages"](guardee_id=101)
    mock_client.get_messages.assert_called_once_with(slug="profiles/101")


def test_get_messages_invalid_guardee_id(tools: dict, mock_client: MagicMock) -> None:
    with pytest.raises(ValueError, match="No guardian role found with id=999"):
        tools["get_messages"](guardee_id=999)


def test_get_notices_with_guardee_id(tools: dict, mock_client: MagicMock) -> None:
    tools["get_notices"](guardee_id=102)
    mock_client.get_notices.assert_called_once_with(slug="profiles/102")


def test_get_notices_invalid_guardee_id(tools: dict, mock_client: MagicMock) -> None:
    with pytest.raises(ValueError, match="No guardian role found"):
        tools["get_notices"](guardee_id=9999)


def test_get_schedule_with_guardee_id(tools: dict, mock_client: MagicMock) -> None:
    tools["get_schedule"](guardee_id=101)
    mock_client.get_schedule.assert_called_once_with(date=None, slug="profiles/101")


def test_get_schedule_invalid_guardee_id(tools: dict, mock_client: MagicMock) -> None:
    with pytest.raises(ValueError, match="No guardian role found"):
        tools["get_schedule"](guardee_id=9999)


def test_get_message_with_guardee_id(tools: dict, mock_client: MagicMock) -> None:
    tools["get_message"](message_id=42, guardee_id=101)
    mock_client.get_message.assert_called_once_with(42, slug="profiles/101")


def test_get_message_without_guardee_id(tools: dict, mock_client: MagicMock) -> None:
    tools["get_message"](message_id=42)
    mock_client.get_message.assert_called_once_with(42, slug=None)


def test_get_notice_with_guardee_id(tools: dict, mock_client: MagicMock) -> None:
    tools["get_notice"](notice_id=7, guardee_id=102)
    mock_client.get_notice.assert_called_once_with(7, slug="profiles/102")


def test_get_notice_without_guardee_id(tools: dict, mock_client: MagicMock) -> None:
    tools["get_notice"](notice_id=7)
    mock_client.get_notice.assert_called_once_with(7, slug=None)
