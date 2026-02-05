"""Collection-related models."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Collection:
    """A Metabase collection (folder for organizing items)."""

    id: int | str  # Can be "root" for root collection
    name: str
    description: str | None = None
    archived: bool = False
    parent_id: int | None = None
    location: str | None = None  # Path like "/1/2/3/"
    personal_owner_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    path: list[str] = field(default_factory=list)  # Human-readable path
    path_ids: list[int] = field(default_factory=list)  # ID-based path
    children: list["Collection"] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


@dataclass
class CollectionItem:
    """An item within a collection (card, dashboard, etc.)."""

    id: int
    name: str
    model: str  # "card", "dashboard", "collection", "dataset", "pulse"
    description: str | None = None
    collection_id: int | None = None
    archived: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_edited_by: str | None = None
    extra: dict = field(default_factory=dict)
