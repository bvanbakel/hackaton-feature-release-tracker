from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from groq import Groq
from groq import APIStatusError
from pydantic import BaseModel

from src.config import AppConfig

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
MODEL = "llama-3.3-70b-versatile"


class ReleaseSummary(BaseModel):
    new_features: list[str]
    deprecations: list[str]
    breaking_changes: list[str]
    client_relevance: list[str]


def _load_system_prompt() -> str:
    return (ROOT / "prompts" / "summarise.txt").read_text()


def summarise_platform_releases(
    platform_name: str,
    releases: list[dict[str, Any]],
    config: AppConfig,
) -> ReleaseSummary | None:
    """Summarise all new releases for a platform into one weekly digest.

    Returns None if the release list is empty.
    Raises groq.APIStatusError on API failure.
    """
    if not releases:
        return None

    client = Groq(api_key=config.groq_api_key)
    user_content = _build_user_message(platform_name, releases, config.summary.max_words_per_platform)

    response = _generate_with_retry(client, user_content)

    usage = response.usage
    logger.info(
        "%s — tokens: %d input, %d output",
        platform_name,
        usage.prompt_tokens,
        usage.completion_tokens,
    )

    return ReleaseSummary.model_validate_json(response.choices[0].message.content)


def _generate_with_retry(client: Groq, user_content: str, max_attempts: int = 4) -> Any:
    """Call Groq with exponential backoff on rate-limit (429) errors."""
    delay = 15
    for attempt in range(1, max_attempts + 1):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": _load_system_prompt()},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
        except APIStatusError as e:
            if e.status_code == 429 and attempt < max_attempts:
                logger.warning("Groq rate limit (attempt %d/%d) — retrying in %ds", attempt, max_attempts, delay)
                time.sleep(delay)
                delay *= 2
            else:
                raise


def _build_user_message(
    platform_name: str,
    releases: list[dict[str, Any]],
    max_words: int,
) -> str:
    lines: list[str] = [
        f"Platform: {platform_name}",
        f"Target summary length: ~{max_words} words across all four fields.",
        "",
        "Raw release notes follow:",
        "",
    ]

    for release in releases:
        lines.append(f"### {release['title']} ({release['date']})")
        content = release.get("raw_content", "").strip()
        if len(content) > 4000:
            content = content[:4000] + "\n[...truncated]"
        lines.append(content)
        lines.append("")

    return "\n".join(lines)
