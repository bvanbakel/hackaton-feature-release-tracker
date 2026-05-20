from __future__ import annotations

import logging
from typing import Callable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import load_config

logger = logging.getLogger(__name__)


def start_scheduler(job: Callable[[], None]) -> None:
    config = load_config()
    scheduler = BlockingScheduler(timezone=config.schedule.timezone)

    parts = config.schedule.cron.split()
    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone=config.schedule.timezone,
    )

    scheduler.add_job(job, trigger)
    logger.info(
        "Scheduler started — cron '%s' (%s)",
        config.schedule.cron,
        config.schedule.timezone,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
