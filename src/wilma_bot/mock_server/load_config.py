from pathlib import Path
import yaml
from wilma_bot.mock_server.config import *


def load_config(path="mock-config.yaml"):
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(f"Config file not found: {file}")
    data = yaml.safe_load(file.read_text(encoding="utf-8"))
    return MockConfig(
        api_version=data.get("api_version", 20),
        users=[
            MockUser(
                username=u["username"],
                password=u["password"],
                account=Account(**u["account"]),
                roles=[
                    Role(
                        type=r["type"],
                        id=r["id"],
                        slug=r["slug"],
                        form_key=r["form_key"],
                        schools=[School(**s) for s in r.get("schools", [])],
                    )
                    for r in u["roles"]
                ],
                session_timeout=u.get("session_timeout", False),
                login_fail=u.get("login_fail", False),
                templates=u.get("templates", {}),
            )
            for u in data.get("users", [])
        ],
        schedule_export=[ScheduleExportTerm(**t) for t in data.get("schedule_export", [])],
        messages=MessagesConfig(**data["messages"]) if "messages" in data else MessagesConfig(),
    )
