from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RawRelease

RSS_URL = "https://docs.databricks.com/aws/en/feed.xml"


class DatabricksScraper(BaseScraper):
    platform_name = "databricks"

    def scrape(self) -> list[RawRelease]:
        response = httpx.get(RSS_URL, timeout=30, follow_redirects=True)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        channel = root.find("channel")
        if channel is None:
            return []

        releases = []
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            description = (item.findtext("description") or "").strip()

            try:
                release_date = parsedate_to_datetime(pub_date).date()
            except Exception:
                continue

            slug = re.sub(r"[^a-z0-9]+", "-", link.rstrip("/").split("/")[-1].lower())
            release_id = f"databricks-{release_date.isoformat()}-{slug}"

            # Strip HTML tags from description for plain text
            raw_content = BeautifulSoup(description, "html.parser").get_text(separator="\n").strip()

            releases.append(RawRelease(
                id=release_id,
                date=release_date,
                title=title,
                raw_content=raw_content,
                url=link,
            ))

        return sorted(releases, key=lambda r: r.date, reverse=True)
