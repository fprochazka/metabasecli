"""Card (saved question/query) models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class VisualizationSettings:
    """Settings for how a card's results are displayed."""

    display: str = "table"  # "table", "bar", "line", "pie", etc.
    settings: dict = field(default_factory=dict)


@dataclass
class CardQuery:
    """The query definition for a card."""

    query_type: str  # "native" or "query" (MBQL)
    database: int

    # For native queries
    native_query: str | None = None
    template_tags: dict = field(default_factory=dict)

    # For MBQL queries
    mbql_query: dict = field(default_factory=dict)


@dataclass
class Card:
    """A Metabase card (saved question/query)."""

    id: int
    name: str
    description: str | None = None
    collection_id: int | None = None
    database_id: int | None = None
    dataset_query: CardQuery | None = None
    display: str = "table"
    visualization_settings: VisualizationSettings | None = None
    parameters: list[dict] = field(default_factory=list)
    archived: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Enriched fields (populated when fetching with details)
    collection_name: str | None = None
    collection_path: list[str] = field(default_factory=list)
    database_name: str | None = None

    # Raw API response for export
    raw_data: dict[str, Any] = field(default_factory=dict)
    extra: dict = field(default_factory=dict)
