"""Search-related API calls.

Provides methods for searching across all Metabase entities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["SearchClient"]

if TYPE_CHECKING:
    from .base import BaseClient


class SearchClient:
    """Client for search-related API calls."""

    def __init__(self, client: BaseClient):
        self._client = client

    def search(
        self,
        query: str,
        models: list[str] | None = None,
        collection_id: int | None = None,
        database_id: int | None = None,
        archived: bool = False,
        created_by: int | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search across all Metabase entities.

        Makes a GET request to /api/search/.

        Args:
            query: The search term.
            models: List of model types to search (e.g., ["card", "dashboard"]).
            collection_id: Limit search to a specific collection.
            database_id: Filter results by database.
            archived: If True, include archived items.
            created_by: Filter by creator user ID.
            limit: Maximum number of results to return.

        Returns:
            Search results dictionary with 'data' and 'total' keys.
        """
        params: dict[str, Any] = {
            "q": query,
            "limit": limit,
        }

        if models:
            # The API accepts multiple 'models' params
            params["models"] = models

        if collection_id is not None:
            params["collection_id"] = collection_id

        if database_id is not None:
            params["table_db_id"] = database_id

        if archived:
            params["archived"] = "true"

        if created_by is not None:
            params["created_by"] = created_by

        response = self._client.get("/search", params=params)

        # The API returns {"data": [...], "total": N, ...}
        if isinstance(response, dict):
            return response

        # Fallback if structure is unexpected
        return {"data": response if isinstance(response, list) else [], "total": 0}
