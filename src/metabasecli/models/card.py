"""Card (saved question/query) models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..utils import parse_datetime


@dataclass
class VisualizationSettings:
    """Settings for how a card's results are displayed."""

    display: str = "table"  # "table", "bar", "line", "pie", etc.
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class CardQuery:
    """The query definition for a card."""

    query_type: str  # "native" or "query" (MBQL)
    database: int

    # For native queries
    native_query: str | None = None
    template_tags: dict[str, Any] = field(default_factory=dict)

    # For MBQL queries
    mbql_query: dict[str, Any] = field(default_factory=dict)


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
    parameters: list[dict[str, Any]] = field(default_factory=list)
    archived: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Enriched fields (populated when fetching with details)
    collection_name: str | None = None
    collection_path: list[str] = field(default_factory=list)
    database_name: str | None = None

    # Raw API response for export
    raw_data: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Card":
        """Create a Card instance from an API response dictionary.

        Args:
            data: Dictionary from Metabase API response.

        Returns:
            Card instance with populated fields.
        """
        # Parse dataset_query if present
        dataset_query = None
        dq = data.get("dataset_query")
        if dq:
            query_type = dq.get("type", "query")
            database = dq.get("database", 0)
            native_query = None
            template_tags = {}
            mbql_query = {}

            if query_type == "native" and "native" in dq:
                native_query = dq["native"].get("query")
                template_tags = dq["native"].get("template-tags", {})
            elif "query" in dq:
                mbql_query = dq["query"]

            dataset_query = CardQuery(
                query_type=query_type,
                database=database,
                native_query=native_query,
                template_tags=template_tags,
                mbql_query=mbql_query,
            )

        # Parse visualization_settings if present
        viz_settings = None
        vs = data.get("visualization_settings")
        if vs:
            viz_settings = VisualizationSettings(
                display=data.get("display", "table"),
                settings=vs,
            )

        # Parse dates
        created_at = parse_datetime(data.get("created_at"))
        updated_at = parse_datetime(data.get("updated_at"))

        # Get collection info
        collection = data.get("collection") or {}
        collection_name = collection.get("name") if isinstance(collection, dict) else None

        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            description=data.get("description"),
            collection_id=data.get("collection_id"),
            database_id=data.get("database_id"),
            dataset_query=dataset_query,
            display=data.get("display", "table"),
            visualization_settings=viz_settings,
            parameters=data.get("parameters", []),
            archived=data.get("archived", False),
            created_at=created_at,
            updated_at=updated_at,
            collection_name=collection_name,
            database_name=data.get("database", {}).get("name") if isinstance(data.get("database"), dict) else None,
            raw_data=data,
        )
