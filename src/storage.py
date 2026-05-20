from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"


def _platform_path(platform: str) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    return DATA_DIR / f"{platform}.json"


def load_platform(platform: str) -> dict[str, Any]:
    path = _platform_path(platform)
    if not path.exists():
        return {"platform": platform, "last_updated": None, "releases": []}
    with open(path) as f:
        return json.load(f)


def save_platform(data: dict[str, Any]) -> None:
    platform = data["platform"]
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    path = _platform_path(platform)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_seen_ids(platform: str) -> set[str]:
    data = load_platform(platform)
    return {r["id"] for r in data["releases"]}


def upsert_releases(platform: str, new_releases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add releases not already stored. Returns only the newly added ones."""
    data = load_platform(platform)
    seen = {r["id"] for r in data["releases"]}

    added = []
    for release in new_releases:
        if release["id"] not in seen:
            data["releases"].append(release)
            seen.add(release["id"])
            added.append(release)

    if added:
        save_platform(data)

    return added


def get_unsummarised(platform: str) -> list[dict[str, Any]]:
    data = load_platform(platform)
    return [r for r in data["releases"] if r.get("summary") is None]


def update_release_summary(platform: str, release_id: str, summary: dict[str, Any]) -> None:
    data = load_platform(platform)
    for release in data["releases"]:
        if release["id"] == release_id:
            release["summary"] = summary
            release["summarised_at"] = datetime.now(timezone.utc).isoformat()
            break
    save_platform(data)
