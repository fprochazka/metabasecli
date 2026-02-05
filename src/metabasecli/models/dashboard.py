"""Dashboard-related models.

Contains dataclasses for Metabase dashboards and dashboard cards.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..utils import parse_datetime

__all__ = ["DashCard", "Dashboard"]


@dataclass
class DashCard:
    """A card placement on a dashboard."""

    id: int
    card_id: int | None = None  # None for text/heading cards
    row: int = 0
    col: int = 0
    size_x: int = 4
    size_y: int = 4
    parameter_mappings: list[dict[str, Any]] = field(default_factory=list)
    visualization_settings: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DashCard":
        """Create a DashCard instance from an API response dictionary.

        Args:
            data: Dictionary from Metabase API response.

        Returns:
            DashCard instance with populated fields.
        """
        return cls(
            id=data.get("id", 0),
            card_id=data.get("card_id"),
            row=data.get("row", 0),
            col=data.get("col", 0),
            size_x=data.get("size_x", 4),
            size_y=data.get("size_y", 4),
            parameter_mappings=data.get("parameter_mappings", []),
            visualization_settings=data.get("visualization_settings", {}),
            extra={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "id",
                    "card_id",
                    "row",
                    "col",
                    "size_x",
                    "size_y",
                    "parameter_mappings",
                    "visualization_settings",
                }
            },
        )


@dataclass
class Dashboard:
    """A Metabase dashboard."""

    id: int
    name: str
    description: str | None = None
    collection_id: int | None = None
    archived: bool = False
    parameters: list[dict[str, Any]] = field(default_factory=list)
    dashcards: list[DashCard] = field(default_factory=list)
    tabs: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Enriched fields (populated when fetching with details)
    collection_name: str | None = None
    collection_path: list[str] = field(default_factory=list)

    # Referenced cards (populated with --include-cards)
    referenced_cards: dict[int, dict[str, Any]] = field(default_factory=dict)

    # Raw API response for export
    raw_data: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Dashboard":
        """Create a Dashboard instance from an API response dictionary.

        Args:
            data: Dictionary from Metabase API response.

        Returns:
            Dashboard instance with populated fields.
        """
        # Parse dashcards
        dashcards = []
        ordered_cards = data.get("ordered_cards") or data.get("dashcards") or []
        for dc in ordered_cards:
            dashcards.append(DashCard.from_dict(dc))

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
            archived=data.get("archived", False),
            parameters=data.get("parameters", []),
            dashcards=dashcards,
            tabs=data.get("tabs", []),
            created_at=created_at,
            updated_at=updated_at,
            collection_name=collection_name,
            raw_data=data,
        )

    def get_unique_card_ids(self) -> list[int]:
        """Get unique card IDs referenced by dashcards.

        Filters out dashcards without a card_id (text cards, heading cards, etc.)

        Returns:
            List of unique card IDs.
        """
        card_ids = set()
        for dashcard in self.dashcards:
            if dashcard.card_id is not None:
                card_ids.add(dashcard.card_id)
        return sorted(card_ids)
