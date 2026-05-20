from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class RawRelease:
    id: str           # Unique, stable identifier (e.g. "databricks-2026-05-05")
    date: date        # Release date
    title: str        # Release title / version label
    raw_content: str  # Full extracted text, pre-summarisation
    url: str = ""     # Source URL for this specific release, if available


class BaseScraper(ABC):
    """Abstract base for all platform scrapers.

    Subclasses must implement `scrape()` and set `platform_name`.
    """

    platform_name: str = ""

    @abstractmethod
    def scrape(self) -> list[RawRelease]:
        """Fetch and parse release notes from the platform.

        Returns a list of RawRelease objects, newest first.
        May raise httpx.HTTPError or platform-specific exceptions on failure.
        """
        ...

    def scrape_since(self, since: date) -> list[RawRelease]:
        """Return only releases on or after `since`."""
        return [r for r in self.scrape() if r.date >= since]
