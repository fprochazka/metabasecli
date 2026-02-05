"""Collection-related API calls.

Provides methods for managing Metabase collections (folders for organizing content).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["CollectionsClient"]

if TYPE_CHECKING:
    from .base import BaseClient


class CollectionsClient:
    """Client for collection-related API calls."""

    def __init__(self, client: BaseClient):
        self._client = client

    def get_tree(self, exclude_archived: bool = True) -> list[dict[str, Any]]:
        """Get the collection hierarchy as a tree.

        Makes a GET request to /api/collection/tree.

        Args:
            exclude_archived: If True, exclude archived collections.

        Returns:
            List of collection dictionaries with nested children.
        """
        params: dict[str, Any] = {}
        if exclude_archived:
            params["exclude-archived"] = "true"

        response = self._client.get("/collection/tree", params=params if params else None)

        # The API returns a list of root-level collections
        if isinstance(response, list):
            return response
        return []

    def get(self, collection_id: int | str) -> dict[str, Any]:
        """Get collection details.

        Makes a GET request to /api/collection/:id.

        Args:
            collection_id: Collection ID or "root" for root collection.

        Returns:
            Collection dictionary with full details.
        """
        return self._client.get(f"/collection/{collection_id}")

    def list_items(
        self,
        collection_id: int | str,
        models: list[str] | None = None,
        archived: bool = False,
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> list[dict[str, Any]]:
        """List items in a collection.

        Makes a GET request to /api/collection/:id/items.

        Args:
            collection_id: Collection ID or "root" for root collection.
            models: Filter by item types (e.g., ["card", "dashboard"]).
            archived: If True, include archived items.
            sort_by: Sort by field: name, last_edited_at, last_edited_by, model.
            sort_dir: Sort direction: asc, desc.

        Returns:
            List of collection item dictionaries.
        """
        params: dict[str, Any] = {}

        if models:
            params["models"] = models

        if archived:
            params["archived"] = "true"

        if sort_by:
            params["sort_column"] = sort_by

        if sort_dir:
            params["sort_direction"] = sort_dir

        response = self._client.get(
            f"/collection/{collection_id}/items",
            params=params if params else None,
        )

        # The API returns {"data": [...], "total": N, ...}
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return []

    def create(
        self,
        name: str,
        description: str | None = None,
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        """Create a new collection.

        Makes a POST request to /api/collection/.

        Args:
            name: Collection name.
            description: Optional description.
            parent_id: Optional parent collection ID.

        Returns:
            Created collection dictionary.
        """
        body: dict[str, Any] = {"name": name}

        if description is not None:
            body["description"] = description

        if parent_id is not None:
            body["parent_id"] = parent_id

        return self._client.post("/collection", json=body)

    def update(
        self,
        collection_id: int,
        name: str | None = None,
        description: str | None = None,
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        """Update a collection.

        Makes a PUT request to /api/collection/:id.

        Args:
            collection_id: The ID of the collection to update.
            name: New name (optional).
            description: New description (optional).
            parent_id: Move to new parent (optional).

        Returns:
            Updated collection dictionary.
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if description is not None:
            body["description"] = description

        if parent_id is not None:
            body["parent_id"] = parent_id

        return self._client.put(f"/collection/{collection_id}", json=body)

    def archive(self, collection_id: int) -> dict[str, Any]:
        """Archive a collection (soft delete).

        Makes a PUT request to /api/collection/:id with archived=true.

        Args:
            collection_id: The ID of the collection to archive.

        Returns:
            Updated collection dictionary.
        """
        return self._client.put(f"/collection/{collection_id}", json={"archived": True})
