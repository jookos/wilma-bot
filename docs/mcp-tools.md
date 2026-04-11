# MCP Tools

Wilma Bot exposes three tools over the MCP protocol. All tools return a single `text` content block containing a JSON string.

Authentication is handled automatically — the client logs in on the first tool call and refreshes the session before each subsequent call.

---

## `get_messages`

Fetch the inbox message list.

### Input schema

```json
{}
```

No parameters.

### Output

A JSON array of message objects as returned by the Wilma API. Structure varies by school configuration but typically includes fields such as `Id`, `Subject`, `SendDate`, `SenderName`, and `IsRead`.

### Example call (MCP)

```json
{
  "method": "tools/call",
  "params": {
    "name": "get_messages",
    "arguments": {}
  }
}
```

---

## `get_schedule`

Fetch the week schedule and school terms. Returns structured lesson events with teacher, room, and time details.

### Input schema

```json
{
  "type": "object",
  "properties": {
    "date": {
      "type": "string",
      "description": "ISO 8601 date (YYYY-MM-DD) for any day within the desired week. Defaults to today if omitted."
    }
  },
  "required": []
}
```

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | string (YYYY-MM-DD) | No | Any day in the target week. Omit for the current week. |

### Output

A JSON object with two keys:

```json
{
  "events": [ ... ],
  "terms": [ ... ]
}
```

#### Event object

```json
{
  "id": 12345,
  "date": {
    "start": "2024-09-02T08:00:00+00:00",
    "end": "2024-09-02T09:30:00+00:00",
    "length_minutes": 90
  },
  "short_name": "MAT",
  "name": "Mathematics",
  "color": "#3399FF",
  "details": {
    "info": "Classroom A101",
    "notes": [],
    "teachers": [
      {
        "id": 42,
        "account_id": "teacher.id",
        "callsign": "EE",
        "name": "Eero Esimerkki"
      }
    ],
    "rooms": [
      {
        "id": "101",
        "short_name": "A101",
        "name": "Classroom A101"
      }
    ],
    "vvt": "",
    "creator": null,
    "editor": null,
    "visible": true
  }
}
```

#### Term object

```json
{
  "name": "Autumn Term 2024",
  "start_date": "2024-08-12T00:00:00",
  "end_date": "2024-12-20T00:00:00"
}
```

### Example call (MCP)

```json
{
  "method": "tools/call",
  "params": {
    "name": "get_schedule",
    "arguments": {
      "date": "2024-09-02"
    }
  }
}
```

---

## `get_notices`

Fetch unread notices and announcements.

### Input schema

```json
{}
```

No parameters.

### Output

A JSON array of notice objects as returned by the Wilma API. Structure varies by school configuration but typically includes fields such as `Id`, `Subject`, `PublishDate`, and `Body`.

### Example call (MCP)

```json
{
  "method": "tools/call",
  "params": {
    "name": "get_notices",
    "arguments": {}
  }
}
```

---

## Error handling

If a tool call fails (authentication error, network error, session expired), the MCP server returns an error response with a descriptive message. The client does not need to manage session state — re-login is automatic.

Common error messages:

| Message | Cause |
|---|---|
| `Failed to login. Check your account credentials and server url` | Wrong username or password |
| `Multi-factor authentication is not yet supported` | MFA is enabled on the account |
| `Unauthorized` | The session role does not have access to the requested resource |
| `Failed to parse schedule data` | Unexpected change in Wilma's HTML response format |
| `Failed to refresh session` | Re-login after session expiry also failed |
