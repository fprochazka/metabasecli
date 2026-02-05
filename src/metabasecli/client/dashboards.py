"""Dashboard-related API calls."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import BaseClient


class DashboardsClient:
    """Client for dashboard-related API calls."""

    def __init__(self, client: BaseClient):
        self._client = client

    def list(self, collection_id: int | None = None) -> list[dict[str, Any]]:
        """List dashboards with optional collection filtering."""
        raise NotImplementedError("List dashboards not implemented")

    def get(self, dashboard_id: int) -> dict[str, Any]:
        """Get dashboard with all dashcard definitions."""
        raise NotImplementedError("Get dashboard not implemented")

    def create(self, dashboard_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new dashboard."""
        raise NotImplementedError("Create dashboard not implemented")

    def update(self, dashboard_id: int, dashboard_data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing dashboard."""
        raise NotImplementedError("Update dashboard not implemented")

    def archive(self, dashboard_id: int) -> dict[str, Any]:
        """Archive a dashboard (soft delete)."""
        raise NotImplementedError("Archive dashboard not implemented")

    def delete(self, dashboard_id: int) -> None:
        """Permanently delete a dashboard."""
        raise NotImplementedError("Delete dashboard not implemented")

    def list_revisions(self, dashboard_id: int) -> list[dict[str, Any]]:
        """List dashboard revisions."""
        raise NotImplementedError("List dashboard revisions not implemented")

    def revert(self, dashboard_id: int, revision_id: int) -> dict[str, Any]:
        """Revert dashboard to a previous revision."""
        raise NotImplementedError("Revert dashboard not implemented")
