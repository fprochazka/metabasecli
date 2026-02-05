"""Shared utility functions for the Metabase CLI."""

import contextlib
from datetime import datetime

__all__ = ["parse_datetime"]


def parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO datetime string, returning None on failure.

    Handles the 'Z' suffix commonly used by Metabase API responses.

    Args:
        value: ISO datetime string, or None.

    Returns:
        Parsed datetime, or None if parsing fails.
    """
    if not value:
        return None
    with contextlib.suppress(ValueError, AttributeError):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None
