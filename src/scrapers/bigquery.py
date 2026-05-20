from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RawRelease

ATOM_NS = "http://www.w3.org/2005/Atom"
FEED_URL = "https://docs.cloud.google.com/feeds/bigquery-release-notes.xml"


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


class BigQueryScraper(BaseScraper):
    platform_name = "bigquery"

    def scrape(self) -> list[RawRelease]:
        response = httpx.get(FEED_URL, timeout=30, follow_redirects=True)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        releases = []
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            title = _text(entry.find(f"{{{ATOM_NS}}}title"))
            updated_str = _text(entry.find(f"{{{ATOM_NS}}}updated"))
            content_el = entry.find(f"{{{ATOM_NS}}}content")
            link_el = entry.find(f"{{{ATOM_NS}}}link[@rel='alternate']")

            url = link_el.get("href", "") if link_el is not None else ""

            try:
                # ISO 8601 with timezone offset
                release_date = datetime.fromisoformat(updated_str).date()
            except Exception:
                continue

            raw_html = _text(content_el)
            raw_content = BeautifulSoup(raw_html, "html.parser").get_text(separator="\n").strip()

            release_id = f"bigquery-{release_date.isoformat()}"

            releases.append(RawRelease(
                id=release_id,
                date=release_date,
                title=title or f"BigQuery release notes {release_date}",
                raw_content=raw_content,
                url=url,
            ))

        return sorted(releases, key=lambda r: r.date, reverse=True)
