"""HTML parsers for Wilma page responses."""

from __future__ import annotations

import datetime
import re
from typing import Any

from bs4 import BeautifulSoup


def parse_notices_html(html: str) -> dict[str, list[dict[str, Any]]]:
    """Parse the /news HTML page into sticky, previous, and current notices.

    Returns a dict with three keys:
      - "sticky":   [{"title": str, "id": int}, ...]
      - "previous": [{"title": str, "id": int}, ...]
      - "current":  [{"title": str, "id": int, "subtitle": str | None,
                      "author": str | None, "date": str | None}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")
    today = datetime.date.today()

    def simple_notices(panel_body: Any) -> list[dict[str, Any]]:
        return [
            {"title": a.get_text(strip=True), "id": int(m.group(1))}
            for a in panel_body.select("a.link-with-arrow")
            if (m := re.search(r"/news/(\d+)$", a.get("href", "")))
        ]

    def find_panel_body(*keywords: str) -> Any:
        for h2 in soup.find_all("h2"):
            if any(kw in h2.get_text() for kw in keywords):
                return h2.find_parent("div", class_="panel-body")
        return None

    sticky_body = find_panel_body("Bestående", "Pysyvät", "Sticky")
    previous_body = find_panel_body("Äldre", "Vanhat", "Previous")

    sticky = simple_notices(sticky_body) if sticky_body else []
    previous = simple_notices(previous_body) if previous_body else []

    # Current notices live in the "tab-content" panel on the left column.
    # Date h2 elements mark the date for the well divs that follow them.
    current: list[dict[str, Any]] = []
    tab_content = soup.find("div", class_="tab-content")
    if tab_content:
        panel_body = tab_content.find("div", class_="panel-body")
        if panel_body:
            current_date: str | None = None
            elements = panel_body.find_all(
                lambda tag: (
                    (tag.name == "h2" and "no-bottom-padding" in tag.get("class", []))
                    or (tag.name == "div" and "well" in tag.get("class", []))
                )
            )
            for elem in elements:
                if elem.name == "h2":
                    date_text = elem.get_text(strip=True).rstrip(".")
                    parts = date_text.split(".")
                    if len(parts) == 2:
                        day, month = int(parts[0]), int(parts[1])
                        year = today.year
                        parsed = datetime.date(year, month, day)
                        if parsed > today:
                            parsed = datetime.date(year - 1, month, day)
                        current_date = parsed.isoformat()
                else:
                    h3 = elem.find("h3")
                    title = h3.get_text(strip=True) if h3 else ""

                    sub_p = elem.find("p", class_="sub-text")
                    subtitle = sub_p.get_text(strip=True) if sub_p else None

                    link = elem.find("a", href=re.compile(r"/news/\d+$"))
                    notice_id: int | None = None
                    if link:
                        m = re.search(r"/news/(\d+)$", link["href"])
                        if m:
                            notice_id = int(m.group(1))

                    author_elem = elem.find("span", class_="tooltip") or elem.find(
                        "a", class_="profile-link"
                    )
                    author = author_elem.get("title") if author_elem else None

                    current.append(
                        {
                            "title": title,
                            "id": notice_id,
                            "subtitle": subtitle,
                            "author": author,
                            "date": current_date,
                        }
                    )

    return {"sticky": sticky, "previous": previous, "current": current}
