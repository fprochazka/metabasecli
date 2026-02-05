"""Collection-related API calls."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import BaseClient


class CollectionsClient:
    """Client for collection-related API calls."""

    def __init__(self, client: "BaseClient"):
        self._client = client

    def get_tree(self, exclude_archived: bool = True) -> list[dict[str, Any]]:
        """Get the collection hierarchy as a tree."""
        raise NotImplementedError("Get collection tree not implemented")

    def get(self, collection_id: int | str) -> dict[str, Any]:
        """Get collection details.

        Args:
            collection_id: Collection ID or "root" for root collection.
        """
        raise NotImplementedError("Get collection not implemented")

    def list_items(
        self,
        collection_id: int | str,
        models: list[str] | None = None,
        archived: bool = False,
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> list[dict[str, Any]]:
        """List items in a collection."""
        raise NotImplementedError("List collection items not implemented")

    def create(
        self,
        name: str,
        description: str | None = None,
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        """Create a new collection."""
        raise NotImplementedError("Create collection not implemented")

    def update(
        self,
        collection_id: int,
        name: str | None = None,
        description: str | None = None,
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        """Update a collection."""
        raise NotImplementedError("Update collection not implemented")

    def archive(self, collection_id: int) -> dict[str, Any]:
        """Archive a collection."""
        raise NotImplementedError("Archive collection not implemented")
