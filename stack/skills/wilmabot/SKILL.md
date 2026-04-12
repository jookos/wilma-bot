---
name: wilmabot
description: Check Wilma school messages, schedule, and notices. Triggers on questions about kids school, teachers, homework, timetable, or anything Wilma-related. Key trigger word - wilma.
---

You are helping the user monitor their children's school communications via the Wilma school management system. The wilma MCP server is already configured — use the `get_messages`, `get_message`, `get_schedule`, `get_notices`, and `get_notice` tools directly.

## State file

Persistent state is stored in a JSON file with this schema:
```json
{"last_seen_message_id": 0, "last_seen_notice_id": 0, "last_checked": ""}
```

At the start of every run, locate the state file by trying these paths in order:
1. `~/.claude/wilma-state.json`
2. `~/.openclaw/wilma-state.json`
3. `~/wilma-state.json`

Use the first path that exists. If none exist, create the file at `~/.claude/wilma-state.json` (or `~/wilma-state.json` if `~/.claude/` does not exist). A missing file is equivalent to `last_seen_message_id: 0, last_seen_notice_id: 0`.

## Local cache

Messages and notices can be cached locally so that full content does not need to be fetched again on repeat requests.

- Cache file locations (same directory as the state file):
    - `wilma-messages-cache.json` — object keyed by message ID (as string), value is the `get_message` response
    - `wilma-notices-cache.json` — object keyed by notice ID (as string), value is the `get_notice` response
- **Before writing a cache file for the first time**, ask the user for permission: _"May I cache Wilma message/notice content locally at `<path>` so I don't have to re-fetch it? (yes/no)"_ Only create the file if the user says yes; remember the answer for the session.
- When fetching a message or notice by ID, check the relevant cache first. If the entry exists, use it directly. Otherwise fetch via MCP and (if caching is enabled) append the result to the cache file.
- Cache entries are permanent — Wilma content does not change after publication.

## Intent parsing

Determine what to do from `$ARGUMENTS` or the conversational context:

- The word **"wilma"** alone, or phrases like "anything on wilma", "new on wilma", "check wilma" → run **messages + notices** flows
- "messages" / "inbox" / "new" → **messages** flow
- "schedule" / "today" / "this week" / "next week" / a specific date → **schedule** flow
- "notices" / "announcements" / "bulletins" → **notices** flow
- "POLL" → **background poller** mode (see below)
- No argument / "check" / "any news" / "anything new" → run **all three** flows

## Messages flow

1. Call `get_messages` (no parameters).
2. Parse the returned JSON array. Sort by `Id` descending.
3. Read `last_seen_message_id` from the state file.
4. Identify new messages: those with `Id` > `last_seen_message_id`.
5. **Default (no special qualifier)**: show a concise list — one line per message with Subject, SenderName, SendDate, and whether it is read. Do NOT include the message body or full content.
6. **Full content**: only if the user explicitly used a word like "full", "whole", "complete", "entire", or "read me the message". For each requested message, call `get_message(message_id)` (checking the local cache first) and display the body. Strip or summarise any HTML if the content is HTML.
7. Highlight new messages (those not previously seen) clearly in the list.
8. After displaying: update `last_seen_message_id` to the highest `Id` seen, set `last_checked` to the current ISO 8601 timestamp, and write the state file.

## Schedule flow

1. If a specific date was mentioned, call `get_schedule` with that date (YYYY-MM-DD). Otherwise call `get_schedule` with no arguments (returns the current week).
2. Group `events[]` by date.
3. Show a compact day-by-day summary. For each day: the date as a header, then each event as:
   `HH:MM–HH:MM  SubjectShortName  (Room · Teacher)`
4. If `terms[]` contains the current date range, mention the active term name at the top.
5. Do not dump raw JSON.

## Notices flow

1. Call `get_notices` (no parameters). The response is an object with three sections: `current`, `sticky`, and `previous`. Each entry has at minimum `title` and `id`; `current` notices also have `subtitle`, `author`, and `date`.
2. Flatten all sections into a single list for tracking purposes (use `id` for deduplication).
3. Read `last_seen_notice_id` from the state file.
4. Identify new notices: those with `id` > `last_seen_notice_id` (across all sections).
5. **Default (no special qualifier)**: show a concise list grouped by section (`current`, `sticky`, `previous`). For each notice: title, author (if present), date (if present), and whether it is new. Do NOT fetch full content unless asked.
6. **Full content**: only if the user explicitly asked for it (words like "full", "read me the notice", "what does it say"). For each requested notice, call `get_notice(notice_id)` (checking the local cache first) and render the `contentHtml` as readable plain text. Also show `audience`, `publisher`, and `visibleUntil` if present.
7. Highlight new notices clearly.
8. After displaying: update `last_seen_notice_id` to the highest `id` seen across all sections, set `last_checked` to the current ISO 8601 timestamp, and write the state file.

## Background poller mode

Activated when `$ARGUMENTS` contains the word **POLL**.

1. Read the state file and note `last_seen_message_id` and `last_seen_notice_id`.
2. Call `get_messages`. Sort by `Id` descending. Find all messages with `Id` > `last_seen_message_id`.
3. Call `get_notices`. Flatten all sections. Find all notices with `id` > `last_seen_notice_id`.
4. If new messages were found:
    - Output a notification starting with **"WILMA ALERT:"** followed by the count and subjects, e.g.:
      `WILMA ALERT: 2 new message(s) — "Re: Field trip permission" from Teacher Smith, "Grade report" from Principal`
5. If new notices were found:
    - Output a notification starting with **"WILMA NOTICE:"** followed by the count and titles, e.g.:
      `WILMA NOTICE: 1 new notice — "Annual parent meeting" by Principal Virtanen`
6. Update `last_seen_message_id` and `last_seen_notice_id` to the highest IDs seen and write the state file.
7. If nothing new: produce no output.

## After each interactive run

If the background poller has not yet been set up (you can assume it hasn't unless the user has told you otherwise), suggest it:

> Want automatic alerts when new messages or notices arrive? You can set up a background check at 9:03, 12:03, and 16:03 on school days in two ways:
>
> **Claude Code** — run `/schedule` and use:
> - Cron: `3 9,12,16 * * 1-5`
> - Prompt: `POLL /wilmabot`
>
> **Any client** — just tell me: _"Check for new Wilma messages and notices at 9:03, 12:03, and 16:03 on school days (Monday–Friday). If there are new messages or notices, alert me."_
