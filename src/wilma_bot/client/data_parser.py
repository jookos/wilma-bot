"""HTML parsers for Wilma page responses."""

from __future__ import annotations

import datetime
import re
from typing import Any

from bs4 import BeautifulSoup


def _parse_wilma_date(day_month: str, today: datetime.date, past: bool = True) -> str:
    """Parse "d.m" into an ISO date string, inferring year from today.

    Args:
        day_month: Date string in "d.m" format.
        today: Reference date for year inference.
        past: When True (default), future dates are assumed to belong to the
              previous year (suitable for publication dates).  When False,
              past dates are assumed to belong to the next year (suitable for
              expiry / "visible until" dates).
    """
    day, month = int(day_month.split(".")[0]), int(day_month.split(".")[1])
    year = today.year
    parsed = datetime.date(year, month, day)
    if past and parsed > today:
        parsed = datetime.date(year - 1, month, day)
    elif not past and parsed < today:
        parsed = datetime.date(year + 1, month, day)
    return parsed.isoformat()


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
                        current_date = _parse_wilma_date(date_text, today)
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


def parse_notice_html(html: str, notice_id: int) -> dict[str, Any]:
    """Parse a single notice page ({slug}/news/{id}) into a structured dict.

    Returns a dict with keys:
      id, title, contentHtml, audience, publisher, date, visibleUntil
    """
    soup = BeautifulSoup(html, "html.parser")
    today = datetime.date.today()

    # The notice content lives in the left column panel-body
    panel_body = soup.select_one("div.col-lg-8 div.panel div.panel-body")
    if panel_body is None:
        return {
            "id": notice_id,
            "title": None,
            "contentHtml": None,
            "audience": None,
            "publisher": None,
            "date": None,
            "visibleUntil": None,
        }

    h2 = panel_body.find("h2")
    title = h2.get_text(strip=True) if h2 else None

    content_div = panel_body.find("div", id="news-content")
    content_html = content_div.decode_contents().strip() if content_div else None

    # Audience text sits in a div.margin-bottom right after the <hr>
    hr = panel_body.find("hr")
    audience_div = hr.find_next_sibling("div", class_="margin-bottom") if hr else None
    audience = audience_div.get_text(strip=True) if audience_div else None

    # Publisher and dates are in div.horizontal-link-container
    link_container = panel_body.find("div", class_="horizontal-link-container")
    publisher: str | None = None
    date: str | None = None
    visible_until: str | None = None

    if link_container:
        # Direct-child spans: [0] icon, [1] author name
        spans = link_container.find_all("span", recursive=False)
        if len(spans) > 1:
            publisher = spans[1].get_text(strip=True)

        for span in link_container.find_all("span", class_="pull-right"):
            text = span.get_text(strip=True)
            # Swedish: "Publicerat d.m." / Finnish: "Julkaistu d.m."
            if text.startswith(("Publicerat", "Julkaistu", "Published")):
                date = _parse_wilma_date(text.split(" ", 1)[1].rstrip("."), today, past=True)
            # Swedish: "Syns tills d.m." / Finnish: "Poistuu d.m."
            elif text.startswith(("Syns tills", "Poistuu", "Visible until")):
                visible_until = _parse_wilma_date(
                    text.rsplit(" ", 1)[1].rstrip("."), today, past=False
                )

    return {
        "id": notice_id,
        "title": title,
        "contentHtml": content_html,
        "audience": audience,
        "publisher": publisher,
        "date": date,
        "visibleUntil": visible_until,
    }
