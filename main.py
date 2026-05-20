import argparse
import logging

from src.config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def run_once() -> None:
    config = load_config()
    logger.info("Loaded config — %d platform(s) enabled", len(config.enabled_platforms()))
    # Phase 2+: scrape → summarise → deliver


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
