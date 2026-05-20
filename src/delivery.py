from __future__ import annotations

import logging
from datetime import date

import httpx

from src.config import AppConfig
from src.summariser import ReleaseSummary

logger = logging.getLogger(__name__)

PLATFORM_LABELS = {
    "databricks": "Databricks",
    "fabric": "Microsoft Fabric",
    "snowflake": "Snowflake",
    "bigquery": "BigQuery",
}


def post_weekly_digest(
    platform_summaries: dict[str, ReleaseSummary | None | str],
    week_of: date,
    config: AppConfig,
) -> None:
    """Post the weekly digest to Google Chat.

    platform_summaries values:
      - ReleaseSummary  → structured summary to format
      - None            → no new releases this week
      - str             → error message for this platform
    """
    text = _format_digest(platform_summaries, week_of)
    _post_to_webhook(text, config.google_chat_webhook_url)
    logger.info("Weekly digest posted to Google Chat")


def _format_digest(
    platform_summaries: dict[str, ReleaseSummary | None | str],
    week_of: date,
) -> str:
    week_label = week_of.strftime("%-d %B %Y")
    lines: list[str] = [
        f"*📊 Weekly Data Platform Release Digest — week of {week_label}*",
        "",
    ]

    for platform_key, summary in platform_summaries.items():
        label = PLATFORM_LABELS.get(platform_key, platform_key.title())
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"*{label}*")
        lines.append("")

        if summary is None:
            lines.append("_No new releases this week._")
        elif isinstance(summary, str):
            lines.append(f"⚠️ _{summary}_")
        else:
            if summary.new_features:
                lines.append("*New Features*")
                for item in summary.new_features:
                    lines.append(f"• {item}")
                lines.append("")

            if summary.deprecations:
                lines.append("*Deprecations & Removals*")
                for item in summary.deprecations:
                    lines.append(f"• {item}")
                lines.append("")

            if summary.breaking_changes:
                lines.append("*Breaking Changes*")
                for item in summary.breaking_changes:
                    lines.append(f"• {item}")
                lines.append("")

            if summary.client_relevance:
                lines.append("*What This Means for Clients*")
                for item in summary.client_relevance:
                    lines.append(f"• {item}")

        lines.append("")

    return "\n".join(lines).strip()


def _post_to_webhook(text: str, webhook_url: str) -> None:
    response = httpx.post(
        webhook_url,
        json={"text": text},
        timeout=15,
    )
    response.raise_for_status()
