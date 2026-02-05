"""Card-related API calls."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import BaseClient


class CardsClient:
    """Client for card (saved question) related API calls."""

    def __init__(self, client: "BaseClient"):
        self._client = client

    def list(
        self,
        filter_type: str | None = None,
        collection_id: int | None = None,
        database_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """List cards with optional filtering."""
        raise NotImplementedError("List cards not implemented")

    def get(self, card_id: int) -> dict[str, Any]:
        """Get card details including full query definition."""
        raise NotImplementedError("Get card not implemented")

    def run(
        self,
        card_id: int,
        parameters: dict | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Execute a card's query and return results."""
        raise NotImplementedError("Run card not implemented")

    def create(self, card_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new card."""
        raise NotImplementedError("Create card not implemented")

    def update(self, card_id: int, card_data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing card."""
        raise NotImplementedError("Update card not implemented")

    def archive(self, card_id: int) -> dict[str, Any]:
        """Archive a card (soft delete)."""
        raise NotImplementedError("Archive card not implemented")

    def delete(self, card_id: int) -> None:
        """Permanently delete a card."""
        raise NotImplementedError("Delete card not implemented")
