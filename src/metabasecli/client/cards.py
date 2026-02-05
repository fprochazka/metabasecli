"""Card-related API calls."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import BaseClient


class CardsClient:
    """Client for card (saved question) related API calls."""

    def __init__(self, client: BaseClient):
        self._client = client

    def list(
        self,
        filter_type: str | None = None,
        collection_id: int | None = None,
        database_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """List cards with optional filtering.

        Makes a GET request to /api/card/.

        Args:
            filter_type: Filter type: all, mine, bookmarked, archived, database, table, using_model.
            collection_id: Filter by collection ID.
            database_id: Filter by database ID (requires filter_type=database).

        Returns:
            List of card dictionaries.
        """
        params: dict[str, Any] = {}

        if filter_type:
            params["f"] = filter_type

        if collection_id is not None:
            params["collection_id"] = collection_id

        if database_id is not None:
            params["database_id"] = database_id

        response = self._client.get("/card", params=params if params else None)

        # The API returns a list of cards directly
        if isinstance(response, list):
            return response
        # Handle case where API wraps in data
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return []

    def get(self, card_id: int) -> dict[str, Any]:
        """Get card details including full query definition.

        Makes a GET request to /api/card/:id.

        Args:
            card_id: The ID of the card to retrieve.

        Returns:
            Card dictionary with full details.
        """
        return self._client.get(f"/card/{card_id}")

    def run(
        self,
        card_id: int,
        parameters: dict | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Execute a card's query and return results.

        Makes a POST request to /api/card/:id/query.

        Args:
            card_id: The ID of the card to execute.
            parameters: Optional query parameters.
            limit: Optional row limit.

        Returns:
            Query results with columns and rows.
        """
        body: dict[str, Any] = {}

        if parameters:
            body["parameters"] = parameters

        # Note: limit might be handled differently depending on Metabase version
        # Some versions use it in the body, others as a query parameter
        if limit is not None:
            body["limit"] = limit

        return self._client.post(f"/card/{card_id}/query", json=body if body else None)

    def create(self, card_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new card.

        Makes a POST request to /api/card/.

        Args:
            card_data: Card definition dict containing at least name, dataset_query, display.

        Returns:
            Created card dictionary.
        """
        return self._client.post("/card", json=card_data)

    def update(self, card_id: int, card_data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing card.

        Makes a PUT request to /api/card/:id.

        Args:
            card_id: The ID of the card to update.
            card_data: Card fields to update.

        Returns:
            Updated card dictionary.
        """
        return self._client.put(f"/card/{card_id}", json=card_data)

    def archive(self, card_id: int) -> dict[str, Any]:
        """Archive a card (soft delete).

        Makes a PUT request to /api/card/:id with archived=true.

        Args:
            card_id: The ID of the card to archive.

        Returns:
            Updated card dictionary.
        """
        return self._client.put(f"/card/{card_id}", json={"archived": True})

    def delete(self, card_id: int) -> None:
        """Permanently delete a card.

        Makes a DELETE request to /api/card/:id.

        Args:
            card_id: The ID of the card to delete.
        """
        self._client.delete(f"/card/{card_id}")
