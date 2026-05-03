from dataclasses import dataclass, field


@dataclass
class Account:
    id: int
    firstname: str
    lastname: str
    username: str
    last_login: str = None


@dataclass
class School:
    id: int
    caption: str
    features: list = field(default_factory=list)


@dataclass
class Role:
    type: str
    id: int
    slug: str
    form_key: str
    name: str = ""
    schools: list = field(default_factory=list)


@dataclass
class MockUser:
    username: str
    password: str
    account: Account
    roles: list
    session_timeout: bool = False
    login_fail: bool = False
    templates: dict = field(default_factory=dict)


@dataclass
class ScheduleExportTerm:
    name: str
    start_date: str
    end_date: str


@dataclass
class MessagesConfig:
    file: str | None = None
    count: int | None = None
    timespan: str | None = None  # e.g. "2y", "6m", "30d"


@dataclass
class MockConfig:
    api_version: int = 20
    users: list = field(default_factory=list)
    schedule_export: list = field(default_factory=list)
    messages: MessagesConfig = field(default_factory=MessagesConfig)
