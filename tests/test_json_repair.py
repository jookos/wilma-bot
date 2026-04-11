"""Tests for the JSON repair utility."""

import json

import pytest

from wilma_bot.client.json_repair import extract_and_repair, repair


class TestRepair:
    def test_quotes_unquoted_keys(self) -> None:
        result = repair("{ Id: 1 }")
        data = json.loads(result)
        assert data["Id"] == 1

    def test_preserves_colons_in_string_values(self) -> None:
        result = repair('{ url: "http://example.com/path" }')
        data = json.loads(result)
        assert data["url"] == "http://example.com/path"

    def test_preserves_colons_in_single_quoted_values(self) -> None:
        result = repair("{ url: 'http://example.com/path' }")
        data = json.loads(result)
        assert data["url"] == "http://example.com/path"

    def test_removes_trailing_semicolon(self) -> None:
        result = repair('{ "Id": 1 };')
        data = json.loads(result)
        assert data["Id"] == 1

    def test_nested_object(self) -> None:
        raw = "{ Id: 1, Lisaaja: { KurreID: 0, Nimi: 'Test' } };"
        data = json.loads(repair(raw))
        assert data["Id"] == 1
        assert data["Lisaaja"]["Nimi"] == "Test"

    def test_already_valid_json_passes_through(self) -> None:
        raw = '{"key": "value", "number": 42}'
        data = json.loads(repair(raw))
        assert data["key"] == "value"
        assert data["number"] == 42


class TestExtractAndRepair:
    def test_extracts_events_json_variable(self) -> None:
        html = """
<html>
<script>
var eventsJSON = {Events: [], DayCount: 5};
</script>
</html>"""
        result = extract_and_repair(html)
        data = json.loads(result)
        assert data["DayCount"] == 5
        assert data["Events"] == []

    def test_raises_on_missing_marker(self) -> None:
        with pytest.raises(ValueError, match="eventsJSON"):
            extract_and_repair("<html><body>No schedule here</body></html>")
