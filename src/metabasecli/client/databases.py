"""Database-related API calls."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import BaseClient


class DatabasesClient:
    """Client for database-related API calls."""

    def __init__(self, client: BaseClient):
        self._client = client

    def list(self, include_tables: bool = False) -> list[dict[str, Any]]:
        """List all databases the user has access to."""
        raise NotImplementedError("List databases not implemented")

    def get(
        self,
        database_id: int,
        include_tables: bool = False,
        include_fields: bool = False,
    ) -> dict[str, Any]:
        """Get database details."""
        raise NotImplementedError("Get database not implemented")

    def get_metadata(
        self,
        database_id: int,
        include_hidden: bool = False,
    ) -> dict[str, Any]:
        """Get complete database metadata including all tables and fields."""
        raise NotImplementedError("Get database metadata not implemented")

    def list_schemas(self, database_id: int) -> list[str]:
        """List all schemas in a database."""
        raise NotImplementedError("List schemas not implemented")
