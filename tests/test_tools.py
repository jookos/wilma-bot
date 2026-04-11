"""Tests for MCP tool handlers."""

import json
from unittest.mock import MagicMock

import pytest

from wilma_bot.client.models import Schedule, ScheduleEvent, ScheduleEventDate, ScheduleEventDetails, Term
from wilma_bot.mcp.tools import REGISTRY

import datetime


@pytest.fixture()
def mock_client() -> MagicMock:
    client = MagicMock()
    client.get_messages.return_value = [{"id": 1, "subject": "Hello"}]
    client.get_notices.return_value = [{"title": "Test notice"}]

    # Build a minimal Schedule object
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


@pytest.mark.asyncio
async def test_get_messages(mock_client: MagicMock) -> None:
    result = await REGISTRY["get_messages"](mock_client, {})
    assert len(result) == 1
    data = json.loads(result[0].text)
    assert data[0]["subject"] == "Hello"


@pytest.mark.asyncio
async def test_get_schedule_no_date(mock_client: MagicMock) -> None:
    result = await REGISTRY["get_schedule"](mock_client, {})
    assert len(result) == 1
    data = json.loads(result[0].text)
    assert len(data["events"]) == 1
    assert data["events"][0]["short_name"] == "Math"
    assert len(data["terms"]) == 1
    mock_client.get_schedule.assert_called_once_with(date=None)


@pytest.mark.asyncio
async def test_get_schedule_with_date(mock_client: MagicMock) -> None:
    result = await REGISTRY["get_schedule"](mock_client, {"date": "2024-01-15"})
    assert len(result) == 1
    mock_client.get_schedule.assert_called_once_with(date=datetime.date(2024, 1, 15))


@pytest.mark.asyncio
async def test_get_notices(mock_client: MagicMock) -> None:
    result = await REGISTRY["get_notices"](mock_client, {})
    assert len(result) == 1
    data = json.loads(result[0].text)
    assert data[0]["title"] == "Test notice"
