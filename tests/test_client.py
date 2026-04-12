"""Tests for the Wilma HTTP client."""

from unittest.mock import MagicMock, patch

import pytest

from wilma_bot.client.wilma import WilmaAuthError, WilmaClient


@pytest.fixture()
def client() -> WilmaClient:
    return WilmaClient(
        base_url="https://example.inschool.fi",
        username="testuser",
        password="testpass",
        validate_server=False,
    )


def _make_response(
    status: int = 200, json_data: object = None, text: str = "", headers: dict | None = None
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    return resp


class TestInitSession:
    def test_returns_session_id_and_version(self, client: WilmaClient) -> None:
        resp = _make_response(
            json_data={"LoginResult": "Failed", "SessionID": "abc123", "ApiVersion": 20}
        )
        with patch.object(client._http, "get", return_value=resp):
            sid, version = client._init_session()
        assert sid == "abc123"
        assert version == 20

    def test_non_200_raises(self, client: WilmaClient) -> None:
        resp = _make_response(status=503)
        with patch.object(client._http, "get", return_value=resp), pytest.raises(WilmaAuthError):
            client._init_session()


class TestPostCredentials:
    def _make_login_resp(self, location: str = "/index") -> MagicMock:
        return _make_response(
            status=302,
            headers={"Location": location, "Set-Cookie": "Wilma2SID=mysid123; path=/"},
        )

    def test_successful_login_returns_sid(self, client: WilmaClient) -> None:
        resp = self._make_login_resp("/index")
        with patch.object(client._http, "post", return_value=resp):
            sid = client._post_credentials("session123")
        assert sid == "mysid123"

    def test_loginfailed_in_location_raises(self, client: WilmaClient) -> None:
        resp = self._make_login_resp("/loginfailed")
        with (
            patch.object(client._http, "post", return_value=resp),
            pytest.raises(WilmaAuthError, match="Failed to login"),
        ):
            client._post_credentials("session123")

    def test_missing_cookie_raises(self, client: WilmaClient) -> None:
        resp = _make_response(status=302, headers={"Location": "/index"})
        with (
            patch.object(client._http, "post", return_value=resp),
            pytest.raises(WilmaAuthError, match="No cookies found"),
        ):
            client._post_credentials("session123")


class TestLogin:
    def _setup_mocks(self, client: WilmaClient) -> None:
        """Wire up all three login steps with happy-path responses."""
        init_resp = _make_response(
            json_data={"LoginResult": "Failed", "SessionID": "sid1", "ApiVersion": 20}
        )
        login_resp = _make_response(
            status=302,
            headers={"Location": "/index", "Set-Cookie": "Wilma2SID=wilma2; path=/"},
        )
        account_resp = _make_response(
            json_data={
                "payload": {
                    "id": 42,
                    "firstname": "Eero",
                    "lastname": "Esimerkki",
                    "username": "testuser",
                    "lastLogin": "2024-01-15T08:30:00",
                    "sessions": [],
                    "multiFactorAuthentication": False,
                }
            }
        )
        roles_resp = _make_response(
            json_data={
                "payload": [
                    {
                        "name": "Eero Esimerkki",
                        "type": "student",
                        "primusId": 42,
                        "formKey": "fk1",
                        "slug": "\\profiles\\42",
                        "schools": [],
                    }
                ]
            }
        )

        client._http.get = MagicMock(side_effect=[init_resp, account_resp, roles_resp])
        client._http.post = MagicMock(return_value=login_resp)

    def test_full_login_sets_authenticated(self, client: WilmaClient) -> None:
        self._setup_mocks(client)
        client.login()
        assert client._authenticated is True

    def test_login_strips_slug_backslashes(self, client: WilmaClient) -> None:
        self._setup_mocks(client)
        client.login()
        assert "\\" not in client._slug

    def test_login_sets_account_info(self, client: WilmaClient) -> None:
        self._setup_mocks(client)
        client.login()
        assert client._account is not None
        assert client._account.firstname == "Eero"
        assert client._account.id == 42


class TestContextManager:
    def test_login_and_logout_called(self, client: WilmaClient) -> None:
        init_resp = _make_response(
            json_data={"LoginResult": "Failed", "SessionID": "s", "ApiVersion": 20}
        )
        login_resp = _make_response(
            status=302,
            headers={"Location": "/index", "Set-Cookie": "Wilma2SID=w; path=/"},
        )
        account_resp = _make_response(
            json_data={
                "payload": {
                    "id": 1,
                    "firstname": "A",
                    "lastname": "B",
                    "username": "a",
                    "lastLogin": "2024-01-01T00:00:00",
                    "sessions": [],
                    "multiFactorAuthentication": False,
                }
            }
        )
        roles_resp = _make_response(
            json_data={
                "payload": [
                    {
                        "name": "A B",
                        "type": "student",
                        "primusId": 1,
                        "formKey": "f",
                        "slug": "\\s\\1",
                        "schools": [],
                    }
                ]
            }
        )
        logout_resp = _make_response()

        client._http.get = MagicMock(side_effect=[init_resp, account_resp, roles_resp, logout_resp])
        client._http.post = MagicMock(return_value=login_resp)

        with client:
            assert client._authenticated is True
        assert client._authenticated is False
