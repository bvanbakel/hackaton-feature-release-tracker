from __future__ import annotations

import re
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RawRelease

BASE_URL = "https://docs.snowflake.com"
INDEX_URL = f"{BASE_URL}/en/release-notes/"

# Matches link text like "May 08-14, 2026 - 10.17" or "May 8, 2026 - 9.45"
_DATE_RE = re.compile(r"([A-Za-z]+ \d{1,2})[,\-–].*?(\d{4})")
# Matches release note paths like /en/release-notes/2026/10_17
_RELEASE_PATH_RE = re.compile(r"^/en/release-notes/\d{4}/[\w_]+$")


def _parse_release_date(link_text: str) -> date | None:
    m = _DATE_RE.search(link_text)
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%B %d %Y").date()
    except ValueError:
        return None


def _fetch_release_content(url: str, client: httpx.Client) -> str:
    try:
        resp = client.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError:
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    # Target the main documentation content area
    main = soup.find("main") or soup.find("article") or soup.find("div", {"role": "main"}) or soup.body
    if main is None:
        return ""

    # Collect headings and paragraphs for a structured text representation
    parts: list[str] = []
    for tag in main.find_all(["h1", "h2", "h3", "p", "li"]):
        text = tag.get_text(separator=" ").strip()
        if text:
            parts.append(text)

    return "\n".join(parts)


class SnowflakeScraper(BaseScraper):
    platform_name = "snowflake"

    def scrape(self) -> list[RawRelease]:
        with httpx.Client() as client:
            resp = client.get(INDEX_URL, timeout=30, follow_redirects=True)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            links = soup.find_all("a", href=_RELEASE_PATH_RE)

            releases = []
            for a in links:
                link_text = a.get_text(separator=" ").strip()
                release_date = _parse_release_date(link_text)
                if release_date is None:
                    continue

                href = a["href"]
                url = f"{BASE_URL}{href}"
                version = href.rstrip("/").split("/")[-1]  # e.g. "10_17"
                release_id = f"snowflake-{version}"

                raw_content = _fetch_release_content(url, client)

                releases.append(RawRelease(
                    id=release_id,
                    date=release_date,
                    title=link_text,
                    raw_content=raw_content,
                    url=url,
                ))

        return sorted(releases, key=lambda r: r.date, reverse=True)
