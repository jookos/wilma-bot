"""Port of the openwilma.js jsonRepair utility.

Wilma schedule responses embed JSON inside an HTML page as a JavaScript
variable. The embedded JSON is not valid — property names are unquoted and
string values may contain unescaped colons. This module repairs it before
handing it to json.loads().
"""

from __future__ import annotations

import re


def repair(raw: str) -> str:
    """Repair malformed Wilma schedule JSON.

    Applies the same transformation sequence as the openwilma.js reference:
    1. Protect colons inside double-quoted string values (placeholder swap).
    2. Protect colons inside single-quoted string values (convert to double-quotes).
    3. Quote unquoted property names.
    4. Restore colon placeholders.
    5. Strip a trailing semicolon if present.
    """
    # 1. Protect colons inside double-quoted values
    raw = re.sub(
        r':\s*"([^"]*)"',
        lambda m: f': "{m.group(1).replace(":", "&tag&")}"',
        raw,
    )
    # 2. Protect colons inside single-quoted values, converting to double-quotes
    raw = re.sub(
        r":\s*'([^']*)'",
        lambda m: f': "{m.group(1).replace(":", "&tag&")}"',
        raw,
    )
    # 3. Quote unquoted property names: identifier: → "identifier":
    raw = re.sub(r"""(['"])?([a-zA-Z0-9_]+)(['"])?\s*:""", r'"\2": ', raw)
    # 4. Restore placeholders
    raw = raw.replace("&tag&", ":")
    # 5. Remove trailing semicolon
    raw = re.sub(r";$", "", raw.rstrip())
    return raw


def extract_and_repair(html: str) -> str:
    """Extract the eventsJSON variable from a schedule HTML page and repair it.

    Raises:
        ValueError: if the eventsJSON variable cannot be found.
    """
    marker = "var eventsJSON = "
    if marker not in html:
        raise ValueError("eventsJSON variable not found in schedule HTML")
    # Take everything after the marker up to the first newline
    blob = html.split(marker)[1].split("\n")[0].strip()
    return repair(blob)
