from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import ServerError
from pydantic import BaseModel

from src.config import AppConfig

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
MODEL = "gemini-2.5-flash"


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
    Raises google.genai exceptions on API failure.
    """
    if not releases:
        return None

    client = genai.Client(api_key=config.gemini_api_key)
    user_content = _build_user_message(platform_name, releases, config.summary.max_words_per_platform)

    response = _generate_with_retry(client, user_content)

    usage = response.usage_metadata
    logger.info(
        "%s — tokens: %d input, %d output",
        platform_name,
        usage.prompt_token_count,
        usage.candidates_token_count,
    )

    return ReleaseSummary.model_validate_json(response.text)


def _generate_with_retry(client: genai.Client, user_content: str, max_attempts: int = 4) -> Any:
    """Call the Gemini API with simple exponential backoff on 503 errors."""
    delay = 15
    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(
                model=MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=_load_system_prompt(),
                    response_mime_type="application/json",
                    response_schema=ReleaseSummary,
                ),
            )
        except ServerError as e:
            if attempt == max_attempts:
                raise
            logger.warning("Gemini 503 (attempt %d/%d) — retrying in %ds", attempt, max_attempts, delay)
            time.sleep(delay)
            delay *= 2


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
