import argparse
import logging
import time
from datetime import date, timedelta

from src.config import load_config
from src.delivery import post_weekly_digest
from src.scrapers.base import RawRelease
from src.scrapers.bigquery import BigQueryScraper
from src.scrapers.databricks import DatabricksScraper
from src.scrapers.fabric import FabricScraper
from src.scrapers.snowflake import SnowflakeScraper
from src.storage import get_last_run_date, get_unsummarised, load_platform, set_last_run_date, upsert_releases
from src.summariser import ReleaseSummary, summarise_platform_releases

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

SCRAPERS = {
    "databricks": DatabricksScraper,
    "snowflake": SnowflakeScraper,
    "bigquery": BigQueryScraper,
    "fabric": FabricScraper,
}


def run_once() -> None:
    config = load_config()
    enabled = config.enabled_platforms()
    logger.info("Starting run — %d platform(s) enabled", len(enabled))

    today = date.today()
    platform_summaries: dict[str, ReleaseSummary | None | str] = {}

    for platform in enabled:
        name = platform.name
        logger.info("Processing %s", name)

        # Use last_run_date if available, otherwise default to 14 days ago (first run)
        since = get_last_run_date(name) or (today - timedelta(days=14))
        logger.info("%s — looking back to %s", name, since)

        # 1. Scrape
        try:
            scraper_cls = SCRAPERS[name]
            releases: list[RawRelease] = scraper_cls().scrape_since(since)
            logger.info("%s — %d release(s) since %s", name, len(releases), since)
        except Exception as e:
            logger.error("Scraping failed for %s: %s", name, e)
            platform_summaries[name] = f"Failed to fetch {platform.name.title()} releases this week."
            continue

        # 2. Store new releases (deduplication handled inside)
        release_dicts = [
            {"id": r.id, "date": str(r.date), "title": r.title, "raw_content": r.raw_content, "summary": None}
            for r in releases
        ]
        new_releases = upsert_releases(name, release_dicts)
        logger.info("%s — %d new (not previously seen)", name, len(new_releases))

        # Also pick up any releases stored in a previous run that failed to summarise
        unsummarised = get_unsummarised(name)
        to_summarise = unsummarised if unsummarised else new_releases

        if not to_summarise:
            platform_summaries[name] = None
            continue

        # 3. Summarise (small delay to stay within per-minute rate limits)
        time.sleep(3)
        try:
            summary = summarise_platform_releases(name, to_summarise, config)
            platform_summaries[name] = summary
        except Exception as e:
            logger.error("Summarisation failed for %s: %s", name, e)
            platform_summaries[name] = f"Failed to summarise {name.title()} releases this week."

    # 4. Deliver
    if not config.google_chat_webhook_url or "..." in config.google_chat_webhook_url:
        logger.warning("No webhook URL configured — printing digest to console instead")
        _print_digest(platform_summaries, today)
        return

    try:
        post_weekly_digest(platform_summaries, today, config)
        # Record successful run date so next run only fetches new releases
        for platform in enabled:
            set_last_run_date(platform.name, today)
    except Exception as e:
        logger.error("Delivery failed: %s", e)
        _print_digest(platform_summaries, today)


def _print_digest(
    platform_summaries: dict[str, ReleaseSummary | None | str],
    week_of: date,
) -> None:
    from src.delivery import _format_digest
    print(_format_digest(platform_summaries, week_of))


def main() -> None:
    parser = argparse.ArgumentParser(description="Feature Release Tracker")
    parser.add_argument("--schedule", action="store_true", help="Run on weekly schedule instead of once")
    args = parser.parse_args()

    if args.schedule:
        from src.scheduler import start_scheduler
        start_scheduler(run_once)
    else:
        run_once()


if __name__ == "__main__":
    main()
