"""Database-related API calls.

Provides methods for listing, retrieving, and syncing databases in Metabase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["DatabasesClient"]

if TYPE_CHECKING:
    from .base import BaseClient


class DatabasesClient:
    """Client for database-related API calls."""

    def __init__(self, client: BaseClient):
        self._client = client

    def list(self, include_tables: bool = False) -> list[dict[str, Any]]:
        """List all databases the user has access to.

        Makes a GET request to /api/database/.

        Args:
            include_tables: If True, include table information for each database.

        Returns:
            List of database dictionaries.
        """
        params: dict[str, Any] = {}
        if include_tables:
            params["include"] = "tables"

        response = self._client.get("/database", params=params if params else None)

        # The API returns {"data": [...]} for list endpoints
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        # Fallback if it returns a list directly
        if isinstance(response, list):
            return response
        return []

    def get(
        self,
        database_id: int,
        include_tables: bool = False,
        include_fields: bool = False,
    ) -> dict[str, Any]:
        """Get database details.

        Makes a GET request to /api/database/:id.

        Args:
            database_id: The ID of the database to retrieve.
            include_tables: If True, include tables.
            include_fields: If True, include tables and their fields.

        Returns:
            Database dictionary.
        """
        params: dict[str, Any] = {}
        if include_fields:
            # include_fields implies include_tables
            params["include"] = "tables.fields"
        elif include_tables:
            params["include"] = "tables"

        return self._client.get(f"/database/{database_id}", params=params if params else None)

    def get_metadata(
        self,
        database_id: int,
        include_hidden: bool = False,
    ) -> dict[str, Any]:
        """Get complete database metadata including all tables and fields.

        Makes a GET request to /api/database/:id/metadata.

        Args:
            database_id: The ID of the database.
            include_hidden: If True, include hidden tables and fields.

        Returns:
            Database metadata dictionary with tables and fields.
        """
        params: dict[str, Any] = {}
        if include_hidden:
            params["include_hidden"] = "true"

        return self._client.get(f"/database/{database_id}/metadata", params=params if params else None)

    def list_schemas(self, database_id: int) -> list[str]:
        """List all schemas in a database.

        Makes a GET request to /api/database/:id/schemas.

        Args:
            database_id: The ID of the database.

        Returns:
            List of schema names.
        """
        response = self._client.get(f"/database/{database_id}/schemas")
        # The API returns a list of schema names
        if isinstance(response, list):
            return response
        return []

    def sync_schema(self, database_id: int) -> dict[str, Any]:
        """Trigger a schema sync for the database.

        Makes a POST request to /api/database/:id/sync_schema.

        Args:
            database_id: The ID of the database.

        Returns:
            Response from the sync request.
        """
        return self._client.post(f"/database/{database_id}/sync_schema")
