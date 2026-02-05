"""Collection-related models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..utils import parse_datetime


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
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Collection":
        """Create a Collection from an API response dictionary."""
        # Build path from effective_ancestors if available
        ancestors = data.get("effective_ancestors", [])
        path = [a.get("name", "") for a in ancestors if a.get("name")]
        path_ids = [a.get("id") for a in ancestors if a.get("id")]

        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            description=data.get("description"),
            archived=data.get("archived", False),
            parent_id=data.get("parent_id"),
            location=data.get("location"),
            personal_owner_id=data.get("personal_owner_id"),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
            path=path,
            path_ids=path_ids,
            extra={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "id",
                    "name",
                    "description",
                    "archived",
                    "parent_id",
                    "location",
                    "personal_owner_id",
                    "created_at",
                    "updated_at",
                    "effective_ancestors",
                }
            },
        )


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
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CollectionItem":
        """Create a CollectionItem from an API response dictionary."""
        # Get last edited by from nested user object if present
        last_edited_by = None
        last_editor = data.get("last_editor")
        if last_editor and isinstance(last_editor, dict):
            last_edited_by = last_editor.get("email") or last_editor.get("common_name")

        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            model=data.get("model", ""),
            description=data.get("description"),
            collection_id=data.get("collection_id"),
            archived=data.get("archived", False),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
            last_edited_by=last_edited_by,
            extra={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "id",
                    "name",
                    "model",
                    "description",
                    "collection_id",
                    "archived",
                    "created_at",
                    "updated_at",
                    "last_editor",
                }
            },
        )
