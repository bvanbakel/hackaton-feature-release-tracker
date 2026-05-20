from __future__ import annotations

from datetime import datetime

import httpx
from bs4 import BeautifulSoup, Tag

from .base import BaseScraper, RawRelease

WHATS_NEW_URL = "https://learn.microsoft.com/en-us/fabric/fundamentals/whats-new"


class FabricScraper(BaseScraper):
    platform_name = "fabric"

    def scrape(self) -> list[RawRelease]:
        response = httpx.get(WHATS_NEW_URL, timeout=30, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Find the "Generally available features" table — 3 columns: Month | Feature | Description
        ga_table = _find_ga_table(soup)
        if ga_table is None:
            return []

        # Group features by month — each month becomes one RawRelease
        monthly: dict[str, list[str]] = {}
        monthly_dates: dict[str, datetime] = {}

        for row in ga_table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            month_text = cols[0].get_text(separator=" ").strip()
            feature_name = cols[1].get_text(separator=" ").strip()
            description = cols[2].get_text(separator=" ").strip()

            if not month_text:
                # Continuation row — use last seen month
                month_text = _last_month(monthly)

            try:
                dt = datetime.strptime(month_text, "%B %Y")
            except ValueError:
                continue

            key = dt.strftime("%Y-%m")
            monthly_dates[key] = dt
            monthly.setdefault(key, [])
            monthly[key].append(f"- {feature_name}: {description}")

        releases = []
        for key, lines in monthly.items():
            dt = monthly_dates[key]
            release_date = dt.date()
            release_id = f"fabric-{key}"
            raw_content = "\n".join(lines)
            releases.append(RawRelease(
                id=release_id,
                date=release_date,
                title=f"Microsoft Fabric — {dt.strftime('%B %Y')} GA features",
                raw_content=raw_content,
                url=WHATS_NEW_URL,
            ))

        return sorted(releases, key=lambda r: r.date, reverse=True)


def _find_ga_table(soup: BeautifulSoup) -> Tag | None:
    for h2 in soup.find_all("h2"):
        if "generally available" in h2.get_text().lower():
            # The table should be the next sibling table element
            sibling = h2.find_next_sibling()
            while sibling:
                if sibling.name == "table":
                    return sibling
                sibling = sibling.find_next_sibling()
    return None


def _last_month(d: dict) -> str:
    return list(d.keys())[-1] if d else ""
