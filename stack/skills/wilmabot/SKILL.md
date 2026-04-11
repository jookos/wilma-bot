---
name: wilmabot
description: Check Wilma school messages, schedule, and notices. Triggers on questions about kids' school, teachers, homework, timetable, or anything Wilma-related. Key trigger word: "wilma".
argument-hint: messages | schedule | notices | new | today | <YYYY-MM-DD>
---

You are helping the user monitor their children's school communications via the Wilma school management system. The wilma MCP server is already configured — use the `get_messages`, `get_schedule`, and `get_notices` tools directly.

## State file

Persistent state is stored in a JSON file with this schema:
```json
{"last_seen_message_id": 0, "last_checked": ""}
```

At the start of every run, locate the state file by trying these paths in order:
1. `~/.claude/wilma-state.json`
2. `~/.openclaw/wilma-state.json`
3. `~/wilma-state.json`

Use the first path that exists. If none exist, create the file at `~/.claude/wilma-state.json` (or `~/wilma-state.json` if `~/.claude/` does not exist). A missing file is equivalent to `last_seen_message_id: 0`.

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
6. **Full content**: only if the user explicitly used a word like "full", "whole", "complete", "entire", or "read me the message".
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

1. Call `get_notices` (no parameters).
2. For each notice, show: Subject, PublishDate, and the first ~80 characters of Body followed by "…" if truncated.
3. Show the full Body only if the user explicitly asked for it.

## Background poller mode

Activated when `$ARGUMENTS` contains the word **POLL**.

1. Read the state file and note `last_seen_message_id`.
2. Call `get_messages`.
3. Sort by `Id` descending. Find all messages with `Id` > `last_seen_message_id`.
4. If new messages were found:
   - Output a notification starting with **"WILMA ALERT:"** followed by the count and subjects, e.g.:
     `WILMA ALERT: 2 new message(s) — "Re: Field trip permission" from Teacher Smith, "Grade report" from Principal`
   - Update and write the state file.
5. If nothing new: produce no output.

## After each interactive run

If the background poller has not yet been set up (you can assume it hasn't unless the user has told you otherwise), suggest it:

> Want automatic alerts when new messages arrive? You can set up a background check at 9:03, 12:03, and 16:03 on school days in two ways:
>
> **Claude Code** — run `/schedule` and use:
> - Cron: `3 9,12,16 * * 1-5`
> - Prompt: `POLL /wilmabot messages`
>
> **Any client** — just tell me: _"Check for new Wilma messages at 9:03, 12:03, and 16:03 on school days (Monday–Friday). If there are new messages, alert me."_
