"""Dashboard-related models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DashCard:
    """A card placement on a dashboard."""

    id: int
    card_id: int | None = None  # None for text/heading cards
    row: int = 0
    col: int = 0
    size_x: int = 4
    size_y: int = 4
    parameter_mappings: list[dict] = field(default_factory=list)
    visualization_settings: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)


@dataclass
class Dashboard:
    """A Metabase dashboard."""

    id: int
    name: str
    description: str | None = None
    collection_id: int | None = None
    archived: bool = False
    parameters: list[dict] = field(default_factory=list)
    dashcards: list[DashCard] = field(default_factory=list)
    tabs: list[dict] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Enriched fields (populated when fetching with details)
    collection_name: str | None = None
    collection_path: list[str] = field(default_factory=list)

    # Referenced cards (populated with --include-cards)
    referenced_cards: dict[int, dict] = field(default_factory=dict)

    # Raw API response for export
    raw_data: dict[str, Any] = field(default_factory=dict)
    extra: dict = field(default_factory=dict)
