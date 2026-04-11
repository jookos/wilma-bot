# Wilma HTTP Protocol

Documented from the `openwilma.js` reference implementation.

---

## Overview

Wilma is a school management platform by Visma (inschool.fi). Each school district runs its own Wilma instance at a URL such as `https://raseborg.inschool.fi`. The API is a mix of JSON REST endpoints and HTML pages that embed JSON in JavaScript variables.

Supported API versions: **18, 19, 20** (checked via `/index_json` on connect).

---

## Base URL

All paths below are relative to the instance base URL, e.g. `https://raseborg.inschool.fi`.

---

## Headers

Every request must include:

```
User-Agent: OpenWilma.js/<version>
```

Authenticated requests must include:

```
Cookie: Wilma2SID=<session_id>
```

---

## Authentication Flow

Authentication is a 3-step process.

### Step 1 — Obtain a SessionID

```
GET /index_json
```

**Response (JSON):**

```json
{
  "LoginResult": "Failed",
  "SessionID": "abc123",
  "ApiVersion": 20
}
```

- `SessionID` is required for the login POST.
- `ApiVersion` must be in `{18, 19, 20}`; otherwise the server is unsupported.

---

### Step 2 — Submit Credentials

```
POST /index_json
Content-Type: application/x-www-form-urlencoded
```

**Request body (form-encoded):**

| Field | Value |
|-------|-------|
| `Login` | username |
| `Password` | password |
| `SESSIONID` | SessionID from step 1 |
| `CompleteJson` | *(empty string)* |
| `format` | `json` |

**Success detection:**

The server responds with a redirect (HTTP 302). Check the `Location` response header:
- If it **contains** `loginfailed` → authentication failed.
- Otherwise → success.

**Cookie extraction:**

Parse the `Set-Cookie` response header for a cookie named `Wilma2SID`. This is the session token used for all subsequent requests.

```
Set-Cookie: Wilma2SID=<value>; path=/; ...
```

---

### Step 3a — Fetch Account Info

```
GET /api/v1/accounts/me
Cookie: Wilma2SID=<value>
```

**Response (JSON):**

```json
{
  "payload": {
    "id": 12345,
    "firstname": "Eero",
    "lastname": "Esimerkki",
    "username": "eero.esimerkki",
    "lastLogin": "2024-01-15T08:30:00Z",
    "sessions": [],
    "multiFactorAuthentication": false
  }
}
```

- HTTP 403 → old account type; fall back to using role data for account identity.
- `multiFactorAuthentication: true` → not yet supported; raise an error.

---

### Step 3b — Fetch Account Roles

```
GET /api/v1/accounts/me/roles
Cookie: Wilma2SID=<value>
```

**Response (JSON):**

```json
{
  "payload": [
    {
      "name": "Eero Esimerkki",
      "type": "student",
      "primusId": 12345,
      "formKey": "abc123",
      "slug": "\\profiles\\12345",
      "schools": [
        {
          "id": 1,
          "caption": "Raseborg School",
          "features": ["schedule", "messages"]
        }
      ]
    }
  ]
}
```

**Role types:** `teacher`, `student`, `personnel`, `guardian`, `workplaceinstructor`, `board`, `passwd`, `trainingcoordinator`, `training`, `applicant`, `applicantguardian`

- Roles with `type == "passwd"` are filtered out but their presence flags that *role control* is required.
- The `slug` field has backslashes that must be stripped: `slug.replace("\\", "")`.
- The first non-passwd role is the default.
- The `slug` is prepended to all subsequent API calls (e.g. `/profiles12345/schedule`).

---

## Session Management

### Session Refresh

Before making schedule (or other) requests, validate the session:

```
GET {slug}/overview
Cookie: Wilma2SID=<value>
```

**Response (JSON):**

```json
{ "LoginResult": true }
```

- `LoginResult: false` → session expired; re-login automatically.
- HTTP 200 with `LoginResult: true` → session is valid.

---

## Endpoints

### Server Discovery

```
GET https://wilmahub.service.inschool.fi/wilmat
```

**Response:**

```json
{
  "wilmat": [
    {
      "url": "https://raseborg.inschool.fi",
      "name": "Raseborg",
      "formerUrl": "https://old.raseborg.inschool.fi",
      "municipalities": [
        { "name_fi": "Raasepori", "name_sv": "Raseborg" }
      ]
    }
  ]
}
```

---

### Messages

```
GET {slug}/messages/list
Cookie: Wilma2SID=<value>
```

Returns a JSON array of message objects. Structure is undocumented; treat as opaque.

---

### Notices / Announcements

```
GET {slug}/notices
Cookie: Wilma2SID=<value>
```

Returns a JSON array of notice objects. Structure is undocumented; treat as opaque.

---

### Schedule

#### Fetch Schedule for a Week

```
GET {slug}/schedule?date=DD.MM.YYYY
Cookie: Wilma2SID=<value>
```

- `date` is in Finnish format: day.month.year (e.g. `15.1.2024`).
- Response is **HTML**, not JSON.
- The schedule data is embedded as a JavaScript variable:

```html
<script>
var eventsJSON = {...};
</script>
```

Extract the JSON blob and repair it before parsing (see [JSON Repair](#json-repair)).

**`eventsJSON` structure:**

```json
{
  "ViewOnly": false,
  "DayCount": 5,
  "DayStarts": 480,
  "DayEnds": 960,
  "ActiveTyyppi": "student",
  "ActiveId": "12345",
  "DialogEnabled": true,
  "Events": [ ... ]
}
```

**Schedule event object:**

| Field | Type | Description |
|-------|------|-------------|
| `Id` | string | Event ID |
| `ViikonPaiva` | string | Finnish weekday name |
| `Date` | string | `DD.MM.YYYY` |
| `Start` | number | Start time in minutes from midnight |
| `End` | number | End time in minutes from midnight |
| `Text` | `{lineNo: string}` | Short name/description (line map) |
| `LongText` | `{lineNo: string}` | Full name/description (line map) |
| `Color` | string | Hex color without `#` |
| `X1`, `Y1`, `X2`, `Y2` | number | Grid position |
| `Lisatieto` | `{lineNo: string}` | Additional info |
| `Muistiinpanot` | `{lineNo: string}` | Notes |
| `OppCount` | `{lineNo: string}` | Student count strings |
| `OpeInfo` | `{line: {line: Teacher}}` | Teacher details |
| `HuoneInfo` | `{line: {line: Room}}` | Room details |
| `Vvt` | string | Internal identifier |
| `Lisaaja` | `{KurreID, Nimi}` | Creator |
| `Muokkaaja` | `{KurreID, Nimi}` | Last editor |
| `NotInGrid` | number | `0` = visible, non-zero = hidden |

**Teacher object:**

```json
{ "kortti": 1, "tunniste": "abc", "lyhenne": "EE", "nimi": "Eero Esimerkki", "sallittu": 1 }
```

**Room object:**

```json
{ "kortti": "101", "lyhenne": "A101", "nimi": "Classroom A101" }
```

**Date/time reconstruction:**

```
Date string: "15.01.2024"  →  parse as month/day/year swap: "01.15.2024"
Start time: 480 minutes    →  08:00 local time (UTC+3 default)
End time:   570 minutes    →  09:30 local time
```

Full datetime = `Date.parse(swapped_date) + minutes * 60 * 1000 + timezone_offset_hours * 3600 * 1000`

#### Fetch Terms / Periods

```
GET {slug}/schedule/export/students/{account_id}/
Cookie: Wilma2SID=<value>
```

**Response (JSON):**

```json
{
  "Schedule": [],
  "Terms": [
    {
      "Name": "Autumn Term 2024",
      "StartDate": "2024-08-12T00:00:00",
      "EndDate": "2024-12-20T00:00:00"
    }
  ]
}
```

---

## JSON Repair

The schedule HTML response contains malformed JSON. Apply these transformations in order before calling `json.loads()`:

1. **Protect colon values in double-quoted strings:** replace `:` inside `"..."` with a placeholder `&tag&`
2. **Protect colon values in single-quoted strings:** same, converting to double quotes
3. **Quote unquoted property names:** `identifier:` → `"identifier":`
4. **Restore placeholders:** `&tag&` → `:`
5. **Remove trailing semicolon** if present

Regex sequence (Python):

```python
import re

def repair_json(raw: str) -> str:
    # 1. Protect colons inside double-quoted values
    raw = re.sub(r':\s*"([^"]*)"', lambda m: f': "{m.group(1).replace(":", "&tag&")}"', raw)
    # 2. Protect colons inside single-quoted values (convert to double quotes)
    raw = re.sub(r":\s*'([^']*)'", lambda m: f': "{m.group(1).replace(":", "&tag&")}"', raw)
    # 3. Quote unquoted property names
    raw = re.sub(r'''(['"])?([a-zA-Z0-9_]+)(['"])?\s*:''', r'"\\2": ', raw)
    # 4. Restore placeholders
    raw = raw.replace("&tag&", ":")
    # 5. Remove trailing semicolon
    raw = re.sub(r";$", "", raw.rstrip())
    return raw
```

---

## Error Conditions

| Condition | Error |
|-----------|-------|
| `/index_json` not HTTP 200 | Unable to get session id |
| No `SessionID` in response | Unable to get session id |
| Login `Location` contains `loginfailed` | Failed to login — check credentials |
| No `Set-Cookie` in login response | No cookies found |
| Cookie parsing fails | Failed to parse session cookies |
| Roles endpoint not HTTP 200 | Unable to fetch essential account role information |
| Role parsing fails | Failed to parse account role data |
| Account info not 200 or 403 | Unable to get essential account information |
| `multiFactorAuthentication: true` | Multi-factor authentication not yet supported |
| Schedule returns 403 | Unauthorized |
| Schedule not HTTP 200 | Unable to fetch schedule |
| Schedule JSON parsing fails | Failed to parse schedule data |
| Terms returns 403 | Unauthorized |
| Terms not HTTP 200 | Unable to fetch periods |
| Overview not HTTP 200 | Unexpected status code while refreshing session |
| `LoginResult: false` in overview | Session expired — re-login attempted |
| Re-login fails | Failed to refresh session |
| `validateServer`: bad URL | Invalid url |
| `validateServer`: not in official list | Not in list of official servers |
| `validateServer`: server unreachable | Failed to connect to server |
| `validateServer`: unsupported version | Unsupported version |

---

## Complete Request Flow

```
connect(url)
├── listServers()         GET wilmahub.service.inschool.fi/wilmat
└── validateServer(url)
    ├── GET {url}/index_json   (check ApiVersion)
    └── return OpenWilma instance

login(username, password)
├── GET  {url}/index_json          → SessionID
├── POST {url}/index_json          → Wilma2SID cookie
├── GET  /api/v1/accounts/me       → AccountInfo
└── GET  /api/v1/accounts/me/roles → roles[], default slug

getSchedule(date)
├── refresh()
│   └── GET {slug}/overview        → LoginResult
├── GET {slug}/schedule?date=...   → HTML → eventsJSON → Events[]
└── GET {slug}/schedule/export/students/{id}/ → Terms[]
```
