"""Local cache for informational instance metadata.

Stores the detected Metabase instance version per profile in
``~/.config/metabasecli/cache.json`` (alongside ``config.toml``). The cache is
purely informational: a corrupt, missing, or unwritable cache file must never
break a command, so every access degrades to "no cached value" rather than
raising.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .config import DEFAULT_CONFIG_DIR, ensure_config_dir

__all__ = [
    "get_cache_path",
    "save_instance_version",
    "get_instance_version",
]

DEFAULT_CACHE_FILE = DEFAULT_CONFIG_DIR / "cache.json"


def get_cache_path() -> Path:
    """Get the path to the cache file."""
    return DEFAULT_CACHE_FILE


def _load_cache() -> dict:
    """Load the cache file, treating any problem as an empty cache."""
    path = get_cache_path()
    if not path.exists():
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}

    return data if isinstance(data, dict) else {}


def save_instance_version(profile: str, url: str, version: str) -> None:
    """Record the detected instance version for a profile.

    Best-effort: a read or write failure is swallowed so it never breaks the
    calling command.

    Args:
        profile: The profile the version was detected for.
        url: The instance URL the version belongs to (used to invalidate the
            entry when a profile is later pointed at a different instance).
        version: The version tag (e.g. ``v1.60.2``).
    """
    cache = _load_cache()
    cache[profile] = {
        "url": url,
        "version": version,
        "checked_at": datetime.now(UTC).isoformat(),
    }

    try:
        ensure_config_dir()
        with open(get_cache_path(), "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except OSError:
        pass


def get_instance_version(profile: str, url: str, max_age_hours: int = 24) -> str | None:
    """Return the cached instance version for a profile.

    Args:
        profile: The profile to look up.
        url: The instance URL the caller expects; a mismatch means the cached
            entry is for a different instance and is ignored.
        max_age_hours: Entries older than this are considered stale.

    Returns:
        The cached version tag, or None on miss, stale entry, or URL mismatch.
    """
    entry = _load_cache().get(profile)
    if not isinstance(entry, dict):
        return None

    if entry.get("url") != url:
        return None

    version = entry.get("version")
    checked_at = entry.get("checked_at")
    if not version or not checked_at:
        return None

    try:
        checked = datetime.fromisoformat(checked_at)
    except (TypeError, ValueError):
        return None
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=UTC)

    if datetime.now(UTC) - checked > timedelta(hours=max_age_hours):
        return None

    return version
