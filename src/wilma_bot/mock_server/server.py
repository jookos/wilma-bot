from pathlib import Path
import json
import random
import re
import secrets
import datetime

_builtin_templates_dir = Path(__file__).parent / "templates"

_default_schedule_events = [
    {
        "EventId": 1,
        "Date": "22.04.2024",
        "Start": 480,
        "End": 540,
        "ShortName": {"11": "Ti", "12": "Ti"},
        "LongName": {"11": "Matematiikka", "12": "Matematiikka"},
        "Text": {"11": "Ti", "12": "Ti"},
        "LongText": {"11": "Matematiikka", "12": "Matematiikka"},
        "Color": "#FF6600",
        "Lisätieto": {"11": "Harjoitus"},
        "Muistiinpanot": {},
        "Vvt": "",
        "Tunti": "1",
        "OpeInfo": {
            "1": {"kortti": 1, "tunniste": "t1", "lyhenne": "MO", "nimi": "Matti Opettaja"}
        },
        "HuomeInfo": {"1": {"kortti": "A1", "lyhenne": "A1", "nimi": "Luokka A1"}},
        "Lisaaja": {"Nimi": "", "Kortti": ""},
        "Muokkaaja": {"Nimi": "", "Kortti": ""},
        "NotInGrid": 0,
        "DayOfWeek": 1,
    },
    {
        "EventId": 2,
        "Date": "22.04.2024",
        "Start": 540,
        "End": 600,
        "ShortName": {"11": "In", "12": "In"},
        "LongName": {"11": "Informatiikka", "12": "Informatiikka"},
        "Text": {"11": "In", "12": "In"},
        "LongText": {"11": "Informatiikka", "12": "Informatiikka"},
        "Color": "#0066FF",
        "Lisätieto": {"11": "Tietokonesali"},
        "Muistiinpanot": {},
        "Vvt": "",
        "Tunti": "2",
        "OpeInfo": {"1": {"kortti": 2, "tunniste": "t2", "lyhenne": "TS", "nimi": "Tiina Sähkö"}},
        "HuomeInfo": {"1": {"kortti": "B2", "lyhenne": "B2", "nimi": "Luokka B2"}},
        "Lisaaja": {"Nimi": "", "Kortti": ""},
        "Muokkaaja": {"Nimi": "", "Kortti": ""},
        "NotInGrid": 0,
        "DayOfWeek": 1,
    },
]
_default_schedule_export = [
    {"Name": "Kevät 2024", "StartDate": "2024-01-08T00:00:00", "EndDate": "2024-05-15T00:00:00"}
]

_SAMPLE_SUBJECTS = [
    "Info",
    "Aktuellt från skolan",
    "Föräldramöte",
    "Skolstart",
    "Utfärd imorgon",
    "Simning på måndag",
    "Gymnastik",
    "Vinterhälsningar",
    "Julhälsningar",
    "Sommarhälsning",
    "Vaccin",
    "Fotografering",
    "Marknadsförsäljning",
    "Läsveckor",
    "Eftis info",
    "Vidarebefordrad info: Hobbyverksamhet",
    "Höstinfo från skolan",
    "Skoltransportenkäten",
]
# (id, display name, sender_type, href_type)
_SAMPLE_SENDERS = [
    (101, "Virtanen Matti (MV)", 1, "teachers"),
    (102, "Korhonen Anna (AK)", 1, "teachers"),
    (103, "Mäkinen Pekka (PM)", 1, "teachers"),
    (104, "Leinonen Sari (SL)", 1, "teachers"),
    (201, "Heikkinen Tuomas (TH)", 3, "personnel"),
    (202, "Nieminen Kaisa (KN)", 3, "personnel"),
]


def _parse_timespan_days(s: str) -> int:
    m = re.fullmatch(r"(\d+)(y|m|d)", s.strip())
    if not m:
        raise ValueError(f"Invalid timespan '{s}': use e.g. '2y', '6m', '30d'")
    n, unit = int(m.group(1)), m.group(2)
    return n * 365 if unit == "y" else n * 30 if unit == "m" else n


def _generate_messages(count: int, timespan: str) -> list:
    days = _parse_timespan_days(timespan)
    now = datetime.datetime.now()
    start = now - datetime.timedelta(days=days)
    total_seconds = int(days * 86400)
    offsets = sorted(random.randint(0, total_seconds) for _ in range(count))
    messages = []
    for i, offset in enumerate(reversed(offsets)):
        ts = start + datetime.timedelta(seconds=offset)
        sid, sname, stype, shref_type = random.choice(_SAMPLE_SENDERS)
        messages.append({
            "Id": 1000000 + i + 1,
            "Subject": random.choice(_SAMPLE_SUBJECTS),
            "TimeStamp": ts.strftime("%Y-%m-%d %H:%M"),
            "Folder": "inbox",
            "SenderId": sid,
            "SenderType": stype,
            "Sender": sname,
            "Senders": [{"Name": sname, "Href": f"/profiles/{shref_type}/{sid}"}],
        })
    return messages


_jinja_env = None


def _get_jinja_env():
    global _jinja_env
    if _jinja_env is None:
        from jinja2 import Environment, FileSystemLoader

        _jinja_env = Environment(loader=FileSystemLoader(_builtin_templates_dir))
    return _jinja_env


_sessions = {}
_app_users = []
_messages_list = []


def configure_server(config_path):
    from wilma_bot.mock_server.load_config import load_config

    global _app_users, _messages_list
    cfg = load_config(config_path)
    _app_users = []
    for u in cfg.users:
        account = {
            "id": u.account.id,
            "firstname": u.account.firstname,
            "lastname": u.account.lastname,
            "username": u.account.username,
            "last_login": u.account.last_login,
        }
        roles = []
        for r in u.roles:
            schools = [
                {"id": s.id, "caption": s.caption, "features": s.features} for s in r.schools
            ]
            roles.append(
                {
                    "name": r.name or str(r.id),
                    "type": r.type,
                    "primusId": r.id,
                    "formKey": r.form_key,
                    "slug": r.slug,
                    "schools": schools,
                }
            )
        _app_users.append(
            {
                "user": {
                    "username": u.username,
                    "password": u.password,
                    "account": account,
                    "roles": roles,
                    "session_timeout": u.session_timeout,
                    "login_fail": u.login_fail,
                    "templates": dict(u.templates),
                    "schedule_export": cfg.schedule_export,
                },
                "username": u.username,
                "slug": roles[0]["slug"],
                "account": account,
            }
        )

    mcfg = cfg.messages
    if mcfg.file:
        _messages_list = json.loads(Path(mcfg.file).read_text(encoding="utf-8"))
    elif mcfg.count and mcfg.timespan:
        _messages_list = _generate_messages(mcfg.count, mcfg.timespan)
    else:
        _messages_list = json.loads((_builtin_templates_dir / "messages_list.json").read_text(encoding="utf-8"))


from fastapi import Request, Response
from fastapi.responses import HTMLResponse, JSONResponse


def _build_ctx(session, **extra):
    user = session.get("user", session)
    ctx = {
        "username": user["username"],
        "account": user.get("account", user),
        "slug": session.get("slug", user.get("slug", "")),
        "session": session,
        "today": "2024-04-22",
        "roles": user.get("roles", []),
        "default_schedule_events": _default_schedule_events,
        "default_schedule_export_terms": _default_schedule_export,
    }
    ctx.update(extra)
    return ctx


def _render(user, filename, **extra):
    ctx = _build_ctx(user, **extra)
    tpl = _get_jinja_env().get_template(filename)
    raw = tpl.render(**ctx)
    if filename.endswith(".json"):
        return json.loads(raw)
    return raw


from fastapi import FastAPI

app = FastAPI(title="Wilma Mock Server")


@app.get("/index_json")
def index_json():
    return JSONResponse(
        {
            "LoginResult": "Failed",
            "SessionID": secrets.token_hex(16),
            "ApiVersion": 20,
        }
    )


@app.post("/index_json")
async def login_page(request: Request):
    data = await request.form()
    username = data.get("Login", "")
    password = data.get("Password", "")
    print(f"Login attempt for user: {username}")
    user = next(
        (u for u in _app_users if u["username"] == username and u["user"]["password"] == password),
        None,
    )
    if user is None or user["user"].get("login_fail"):
        print(f"Login failed for user: {username}")
        return Response(status_code=302, headers={"Location": "/LoginFailed"})
    sid = secrets.token_hex(32)
    _sessions[sid] = {
        "user": user["user"],
        "username": username,
        "slug": user["slug"],
        "account": user["account"],
    }
    response = Response(
        status_code=302,
        headers={
            "Location": "/",
        },
    )
    response.set_cookie(key="Wilma2SID", value=sid, path="/")
    print(f"Login successful for user: {username}, SID: {sid}")
    return response


@app.get("/api/v1/accounts/me")
def api_account_me(request: Request):
    sid = request.cookies.get("Wilma2SID")
    if not sid or sid not in _sessions:
        return Response(status_code=401)
    user = _sessions[sid]["user"]
    if user.get("session_timeout"):
        return Response(status_code=403)
    acct = user["account"]
    return JSONResponse(
        {
            "payload": {
                "id": acct["id"],
                "firstname": acct["firstname"],
                "lastname": acct["lastname"],
                "username": acct["username"],
                "lastLogin": acct["last_login"] or "1970-01-01T00:00:00",
                "sessions": [],
                "multiFactorAuthentication": False,
            }
        }
    )


@app.get("/api/v1/accounts/me/roles")
def api_account_me_roles(request: Request):
    sid = request.cookies.get("Wilma2SID")
    if not sid or sid not in _sessions:
        return Response(status_code=401)
    user = _sessions[sid]["user"]
    roles = []
    for r in user["roles"]:
        roles.append({k: (v.replace("\\", "") if isinstance(v, str) else v) for k, v in r.items()})
    return {"payload": roles}


@app.get("/{path:path}")
async def mock_wilma(request: Request):
    sid = request.cookies.get("Wilma2SID")
    if not sid or sid not in _sessions:
        return Response(status_code=401)
    session = _sessions[sid]
    current = session["user"]
    if current.get("session_timeout"):
        return Response(status_code=401)

    path = request.url.path.strip("/").split("/")
    if not path:
        return Response(status_code=404)

    if "logout" in path:
        _sessions.pop(sid, None)
        return Response(status_code=200)

    if "overview" in path:
        return {"LoginResult": True}

    # Remove leading slug parts like profiles/42
    # The first 2 parts (profiles/42) are always the role slug
    idx = 0
    if len(path) >= 2 and path[0] == "profiles":
        idx = 2
    elif len(path) >= 1 and path[0].startswith("profiles1"):
        # slug without separator (profiles123/schedule)
        num = ""
        for c in path[0]:
            if c.isdigit():
                num += c
            else:
                break
        if num:
            idx = 1 + len(num) + 1 if path[0][len(num) :].startswith("/") else 1 + len(num)
        if idx == 0:
            idx = 1

    remainder = path[idx:]

    # messages/list
    if len(remainder) >= 2 and remainder[0] == "messages":
        if remainder[1] == "list":
            return {"Messages": _messages_list, "Status": 200}
        if remainder[1].isdigit():
            return _render(
                session,
                "messages_detail.json",
                message_id=int(remainder[1]),
                message_title=f"Msg {remainder[1]}",
            )

    # news
    if len(remainder) >= 1 and remainder[0] == "news":
        if len(remainder) == 1 or not remainder[1].isdigit():
            ctx = _build_ctx(
                session,
                sticky_notices=[{"id": 100, "title": "Pysyän ilmoitus"}],
                current_notices=[
                    {"id": 201, "title": "Kevän tapahtumat", "subtitle": "Koulu 2024"},
                    {"id": 202, "title": "Vanhat tiedot", "subtitle": "Tietoa oppilaalle"},
                ],
            )
            return HTMLResponse(
                content=_get_jinja_env().get_template("news_list.html").render(**ctx)
            )
        if len(remainder) >= 2 and remainder[1].isdigit():
            nid = int(remainder[1])
            ctx = _build_ctx(
                session,
                notice_id=nid,
                notice_title=f"Ilmoitus {nid}",
                notice_content="<p>Tama on mock-ilmoituksen sisältö.</p>",
                notice_date="10.4.",
                notice_publisher="Mock Opastaja",
                notice_audience="Kaikki",
                notice_visible_until="15.5.",
            )
            return HTMLResponse(
                content=_get_jinja_env().get_template("notice_detail.html").render(**ctx)
            )

    # schedule
    if len(remainder) >= 1 and remainder[0] == "schedule":
        if len(remainder) == 1:
            ctx = _build_ctx(session, date="22.04.2024", schedule_data=_default_schedule_events)
            return HTMLResponse(
                content=_get_jinja_env().get_template("schedule.html").render(**ctx)
            )
        if len(remainder) == 4 and remainder[1] == "export" and remainder[2] == "students":
            terms = current.get("schedule_export") or _default_schedule_export
            # Convert dataclass objects to dicts for JSON serialization
            term_dicts = (
                [{"Name": t.name, "StartDate": t.start_date, "EndDate": t.end_date} for t in terms]
                if hasattr(terms[0], "name")
                else terms
            )
            tpl = _get_jinja_env().get_template("schedule_export.json")
            return JSONResponse(
                json.loads(tpl.render(**_build_ctx(session, schedule_terms=term_dicts)))
            )

    return Response(status_code=404)
