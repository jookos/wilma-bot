"""Full Wilma HTTP client implementing the protocol documented in docs/protocol.md."""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any

import requests

from wilma_bot.client.data_parser import parse_notices_html
from wilma_bot.client.json_repair import extract_and_repair
from wilma_bot.client.models import (
    Account,
    AccountInfo,
    AccountRole,
    Role,
    RoleType,
    Schedule,
    ScheduleEvent,
    ScheduleEventDate,
    ScheduleEventDetails,
    SessionInit,
    Teacher,
    Term,
    WilmaServer,
    Room,
)

logger = logging.getLogger(__name__)

SUPPORTED_API_VERSIONS = {18, 19, 20, 30}
SERVER_LIST_URL = "https://wilmahub.service.inschool.fi/wilmat"
USER_AGENT = "WilmaBot.py/0.1.0"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class WilmaError(Exception):
    """Base class for all Wilma client errors."""


class WilmaAuthError(WilmaError):
    """Authentication failed."""


class WilmaSessionError(WilmaError):
    """Session is invalid or expired and could not be refreshed."""


class WilmaServerError(WilmaError):
    """Server is invalid or unreachable."""


class WilmaMFAError(WilmaError):
    """Multi-factor authentication is required but not supported."""


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------


class WilmaClient:
    """Stateful Wilma session client.

    Typical usage::

        client = WilmaClient(base_url, username, password)
        client.login()
        schedule = client.get_schedule()
        client.logout()

    Or as a context manager::

        with WilmaClient(base_url, username, password) as client:
            schedule = client.get_schedule()
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: int = 30,
        validate_server: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self._password = password
        self.timeout = timeout
        self.validate_server = validate_server

        self._http = requests.Session()
        self._http.headers["User-Agent"] = USER_AGENT

        # Set after login
        self._session_id: str | None = None
        self._account: Account | None = None
        self._roles: list[Role] = []
        self._slug: str = ""
        self._authenticated = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def account(self) -> Account:
        if self._account is None:
            raise WilmaSessionError("Not authenticated")
        return self._account

    @property
    def roles(self) -> list[Role]:
        return self._roles

    @property
    def current_role(self) -> Role | None:
        return next((r for r in self._roles if r.slug == self._slug), None)

    # ------------------------------------------------------------------
    # Server discovery
    # ------------------------------------------------------------------

    @classmethod
    def list_servers(cls, timeout: int = 30) -> list[WilmaServer]:
        """Return the official list of Wilma server instances."""
        resp = requests.get(SERVER_LIST_URL, timeout=timeout, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        data = resp.json()
        return [WilmaServer.model_validate(s) for s in data["wilmat"]]

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Full 3-step authentication.

        Raises:
            WilmaAuthError: on bad credentials or unexpected server response.
            WilmaMFAError: if MFA is enabled on the account.
            WilmaServerError: if the server is invalid or an unsupported version.
        """
        if self.validate_server:
            self._check_server()

        session_id, api_version = self._init_session()
        logger.debug("Got SessionID %s (API v%d)", session_id, api_version)

        wilma2sid = self._post_credentials(session_id)
        logger.debug("Got Wilma2SID cookie")

        self._session_id = wilma2sid
        self._http.cookies.set("Wilma2SID", wilma2sid)

        account, roles, slug = self._fetch_account_and_roles()

        self._account = account
        self._roles = roles
        self._slug = slug
        self._authenticated = True
        logger.info("Authenticated as %s %s", account.firstname, account.lastname)

    def logout(self) -> None:
        """Invalidate the server session and clear local state."""
        if self._authenticated:
            try:
                self._http.get(f"{self.base_url}/logout", timeout=self.timeout)
            except requests.RequestException:
                pass
        self._session_id = None
        self._account = None
        self._roles = []
        self._slug = ""
        self._authenticated = False

    def set_role(self, role: str | int) -> None:
        """Switch the active role by slug or primusId.

        Args:
            role: role slug string or integer primusId.

        Raises:
            WilmaError: if role is not found in the role list.
        """
        match = next(
            (r for r in self._roles if r.slug == role or r.id == role),
            None,
        )
        if match is None:
            raise WilmaError(f"Unknown role: {role!r}")
        self._slug = match.slug
        if self._account:
            parts = match.name.strip().split(" ", 1)
            self._account = Account(
                id=match.id,
                firstname=parts[0],
                lastname=parts[1] if len(parts) > 1 else "",
                username=self._account.username,
                last_login=None,
            )

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    def get_messages(self) -> list[dict[str, Any]]:
        """Return inbox messages."""
        self._ensure_fresh()
        res = self._get(f"{self._slug}/messages/list")
        res.raise_for_status()
        return res.json()  # type: ignore[no-any-return]

    def get_message(self, message_id: int) -> list[dict[str, Any]]:
        """Return an inbox message."""
        self._ensure_fresh()
        res = self._get(f"{self._slug}/messages/{message_id}", params={"format": "json"})
        res.raise_for_status()
        return res.json()  # type: ignore[no-any-return]

    def get_notices(self) -> dict[str, list[dict[str, Any]]]:
        """Return notices from the news board, split into sticky, previous, and current."""
        self._ensure_fresh()
        res = self._get(f"{self._slug}/news")
        res.raise_for_status()
        return parse_notices_html(res.text)

    def get_schedule(
        self,
        date: datetime.date | None = None,
        timezone_offset_hours: int = 3,
    ) -> Schedule:
        """Fetch the week schedule and terms for a given date.

        Args:
            date: The date to fetch the schedule for (any day in the target week).
                  Defaults to today.
            timezone_offset_hours: Timezone offset added when computing UTC datetimes.
                  Default is 3 (UTC+3, Helsinki time).

        Returns:
            A :class:`Schedule` containing events and terms.
        """
        self._ensure_fresh()

        if date is None:
            date = datetime.date.today()

        date_param = f"{date.day}.{date.month}.{date.year}"
        res = self._get(f"{self._slug}/schedule", params={"date": date_param})

        if res.status_code == 403:
            raise WilmaError("Unauthorized")
        if res.status_code != 200:
            raise WilmaError("Unable to fetch schedule")

        # Parse HTML → eventsJSON
        try:
            repaired = extract_and_repair(res.text)
            schedule_data = json.loads(repaired)
        except Exception as exc:
            raise WilmaError("Failed to parse schedule data") from exc

        events = self._parse_events(schedule_data.get("Events", []), timezone_offset_hours)

        # Fetch terms
        account_id = self.account.id
        terms_res = self._get(f"{self._slug}/schedule/export/students/{account_id}/")

        if terms_res.status_code == 403:
            raise WilmaError("Unauthorized")
        if terms_res.status_code != 200:
            raise WilmaError("Unable to fetch periods")

        terms_data = terms_res.json()
        terms = [
            Term(
                name=t["Name"],
                start_date=datetime.datetime.fromisoformat(t["StartDate"]),
                end_date=datetime.datetime.fromisoformat(t["EndDate"]),
            )
            for t in terms_data.get("Terms", [])
        ]

        return Schedule(events=events, terms=terms)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_server(self) -> None:
        """Validate that the base_url is an official, supported Wilma server."""
        try:
            servers = self.list_servers(self.timeout)
        except requests.RequestException as exc:
            raise WilmaServerError("Failed to request list of Wilma servers") from exc

        if not any(s.url == self.base_url for s in servers):
            raise WilmaServerError("Not in list of official servers")

        resp = self._http.get(f"{self.base_url}/index_json", timeout=self.timeout)
        if resp.status_code != 200:
            raise WilmaServerError("Failed to connect to server")

        info = resp.json()
        if info.get("ApiVersion") not in SUPPORTED_API_VERSIONS:
            raise WilmaServerError(f"Unsupported API version: {info.get('ApiVersion')}")

    def _init_session(self) -> tuple[str, int]:
        """GET /index_json — obtain SessionID and ApiVersion."""
        resp = self._http.get(f"{self.base_url}/index_json", timeout=self.timeout)
        if resp.status_code != 200:
            raise WilmaAuthError("Unable to get session id")
        init = SessionInit.model_validate(resp.json())
        if init.api_version not in SUPPORTED_API_VERSIONS:
            raise WilmaServerError(f"Unsupported API version: {init.api_version}")
        return init.session_id, init.api_version

    def _post_credentials(self, session_id: str) -> str:
        """POST /index_json — submit credentials and extract Wilma2SID cookie."""
        payload = {
            "Login": self.username,
            "Password": self._password,
            "SESSIONID": session_id,
            "CompleteJson": "",
            "format": "json",
        }
        resp = self._http.post(
            f"{self.base_url}/index_json",
            data=payload,
            allow_redirects=False,
            timeout=self.timeout,
        )

        location = resp.headers.get("Location", "loginfailed")
        if "loginfailed" in location:
            raise WilmaAuthError(
                "Failed to login. Check your account credentials and server url"
            )

        # Extract Wilma2SID from Set-Cookie
        set_cookie = resp.headers.get("Set-Cookie", "")
        if not set_cookie:
            raise WilmaAuthError("No cookies found")

        try:
            wilma2sid = next(
                part.split("=", 1)[1].split(";")[0]
                for part in set_cookie.split(", ")
                if part.startswith("Wilma2SID=")
            )
        except StopIteration as exc:
            raise WilmaAuthError("Failed to parse session cookies") from exc

        return wilma2sid

    def _fetch_account_and_roles(self) -> tuple[Account, list[Role], str]:
        """Fetch account info and roles after getting Wilma2SID."""
        account_resp = self._http.get(
            f"{self.base_url}/api/v1/accounts/me", timeout=self.timeout
        )
        roles_resp = self._http.get(
            f"{self.base_url}/api/v1/accounts/me/roles", timeout=self.timeout
        )

        # Parse roles first (always required)
        if roles_resp.status_code != 200:
            raise WilmaAuthError("Unable to fetch essential account role information")

        try:
            raw_roles: list[dict[str, Any]] = roles_resp.json()["payload"]
            role_control_required = any(r["type"] == "passwd" for r in raw_roles)
            roles = [
                Role(
                    name=r["name"],
                    type=RoleType(r["type"]),
                    id=r["primusId"],
                    is_default=(i == 0),
                    slug=r["slug"].replace("\\", ""),
                    form_key=r["formKey"],
                )
                for i, r in enumerate(raw_roles)
                if r["type"] != "passwd"
            ]
        except Exception as exc:
            raise WilmaAuthError("Failed to parse account role data") from exc

        default_slug = roles[0].slug if roles else ""

        # Parse account info
        if account_resp.status_code == 403:
            # Old account type — derive identity from the default role
            parts = roles[0].name.strip().split(" ", 1)
            account = Account(
                id=roles[0].id,
                firstname=parts[0],
                lastname=parts[1] if len(parts) > 1 else "",
                username=self.username,
            )
        elif account_resp.status_code == 200:
            info = AccountInfo.model_validate(account_resp.json()["payload"])
            if info.multi_factor_authentication:
                raise WilmaMFAError("Multi-factor authentication is not yet supported")

            if role_control_required:
                parts = roles[0].name.strip().split(" ", 1)
                account = Account(
                    id=roles[0].id,
                    firstname=parts[0],
                    lastname=parts[1] if len(parts) > 1 else "",
                    username=self.username,
                )
            else:
                last_login: datetime.datetime | None = None
                try:
                    last_login = datetime.datetime.fromisoformat(info.last_login)
                except ValueError:
                    pass
                account = Account(
                    id=info.id,
                    firstname=info.firstname,
                    lastname=info.lastname,
                    username=info.username,
                    last_login=last_login,
                )
        else:
            raise WilmaAuthError("Unable to get essential account information")

        return account, roles, default_slug

    def _ensure_fresh(self) -> None:
        """Ensure session is valid; re-login if needed."""
        if not self._authenticated:
            self.login()
            return
        self._refresh()

    def _refresh(self) -> None:
        """Check session validity via /overview; re-login if expired."""
        try:
            resp = self._get(f"{self._slug}/overview")
        except requests.RequestException as exc:
            raise WilmaSessionError("Unexpected error while refreshing session") from exc

        if resp.status_code != 200:
            raise WilmaSessionError(
                "Received an unexpected status code while refreshing session state"
            )

        state = resp.json()
        if state.get("LoginResult") is False:
            logger.info("Session expired, re-authenticating")
            try:
                self._authenticated = False
                self.login()
            except WilmaError as exc:
                raise WilmaSessionError("Failed to refresh session") from exc

    def _get(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> requests.Response:
        """Issue a GET against base_url + path."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        return self._http.get(url, params=params, timeout=self.timeout)

    @staticmethod
    def _parse_events(raw_events: list[dict[str, Any]], tz_hours: int) -> list[ScheduleEvent]:
        events: list[ScheduleEvent] = []
        for ev in raw_events:
            # Date: "DD.MM.YYYY" → swap to "MM.DD.YYYY" for parsing
            day, month, year = ev["Date"].split(".")
            base_ts = datetime.datetime(
                int(year), int(month), int(day), tzinfo=datetime.timezone.utc
            )
            tz_delta = datetime.timedelta(hours=tz_hours)
            start_dt = base_ts + datetime.timedelta(minutes=ev["Start"]) - tz_delta
            end_dt = base_ts + datetime.timedelta(minutes=ev["End"]) - tz_delta

            teachers = [
                Teacher.model_validate(t)
                for line1 in ev.get("OpeInfo", {}).values()
                for t in line1.values()
            ]
            rooms = [
                Room.model_validate(r)
                for line1 in ev.get("HuoneInfo", {}).values()
                for r in line1.values()
            ]

            opp_count_raw = ev.get("OppCount", {}).get("0", "0 students")
            try:
                student_count = int(opp_count_raw.split(" ")[0])
            except (ValueError, AttributeError):
                student_count = 0

            creator_raw = ev.get("Lisaaja", {}).get("Nimi", "")
            editor_raw = ev.get("Muokkaaja", {}).get("Nimi", "")
            creator = creator_raw.split("  ", 1)[1] if "  " in creator_raw else None
            editor = editor_raw.split("  ", 1)[1] if "  " in editor_raw else None

            events.append(
                ScheduleEvent(
                    id=int(ev["Id"]),
                    date=ScheduleEventDate(
                        start=start_dt,
                        end=end_dt,
                        length_minutes=(ev["End"] - ev["Start"]),
                    ),
                    short_name="\n".join(ev.get("Text", {}).values()),
                    name="\n".join(ev.get("LongText", {}).values()),
                    color=f"#{ev.get('Color', '')}",
                    details=ScheduleEventDetails(
                        info="\n".join(v.strip() for v in ev.get("Lisatieto", {}).values()),
                        notes=[v.strip() for v in ev.get("Muistiinpanot", {}).values()],
                        teachers=teachers,
                        rooms=rooms,
                        vvt=ev.get("Vvt", ""),
                        creator=creator,
                        editor=editor,
                        visible=ev.get("NotInGrid", 0) == 0,
                    ),
                )
            )
        return events

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "WilmaClient":
        self.login()
        return self

    def __exit__(self, *_: object) -> None:
        self.logout()
