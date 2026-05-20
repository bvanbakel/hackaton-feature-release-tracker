from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import anthropic
from pydantic import BaseModel

from src.config import AppConfig

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
MODEL = "claude-sonnet-4-6"


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
    Raises anthropic.APIError on API failure (caller should handle and skip platform).
    """
    if not releases:
        return None

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    system_prompt = _load_system_prompt()
    user_content = _build_user_message(platform_name, releases, config.summary.max_words_per_platform)

    response = client.messages.parse(
        model=MODEL,
        max_tokens=2048,
        system=[{
            "type": "text",
            "text": system_prompt,
            # Prompt caching: system prompt is stable across all platforms and runs.
            # Cache write cost is offset after ~2 requests per cache TTL window.
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_content}],
        output_format=ReleaseSummary,
    )

    logger.info(
        "%s — tokens: %d input (%d cached, %d new), %d output",
        platform_name,
        response.usage.input_tokens + response.usage.cache_read_input_tokens,
        response.usage.cache_read_input_tokens,
        response.usage.input_tokens,
        response.usage.output_tokens,
    )

    return response.parsed_output


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
        # Cap individual release content to avoid blowing the context window
        content = release.get("raw_content", "").strip()
        if len(content) > 4000:
            content = content[:4000] + "\n[...truncated]"
        lines.append(content)
        lines.append("")

    return "\n".join(lines)
