from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent


@dataclass
class PlatformConfig:
    name: str
    enabled: bool
    url: str


@dataclass
class ScheduleConfig:
    cron: str
    timezone: str


@dataclass
class BackfillConfig:
    start_date: str  # ISO date string, e.g. "2026-05-01"


@dataclass
class SummaryConfig:
    max_words_per_platform: int
    language: str


@dataclass
class AppConfig:
    platforms: dict[str, PlatformConfig]
    schedule: ScheduleConfig
    backfill: BackfillConfig
    summary: SummaryConfig
    anthropic_api_key: str
    google_chat_webhook_url: str

    def enabled_platforms(self) -> list[PlatformConfig]:
        return [p for p in self.platforms.values() if p.enabled]


def load_config(config_path: Path | None = None, env_path: Path | None = None) -> AppConfig:
    load_dotenv(env_path or ROOT / ".env")

    config_file = config_path or ROOT / "config.yaml"
    with open(config_file) as f:
        raw = yaml.safe_load(f)

    platforms = {
        name: PlatformConfig(name=name, enabled=cfg["enabled"], url=cfg["url"])
        for name, cfg in raw["platforms"].items()
    }

    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "")

    return AppConfig(
        platforms=platforms,
        schedule=ScheduleConfig(**raw["schedule"]),
        backfill=BackfillConfig(**raw["backfill"]),
        summary=SummaryConfig(**raw["summary"]),
        anthropic_api_key=anthropic_api_key,
        google_chat_webhook_url=webhook_url,
    )
