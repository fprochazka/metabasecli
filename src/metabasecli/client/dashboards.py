"""Dashboard-related API calls.

Provides methods for managing Metabase dashboards, including revisions and revert.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["DashboardsClient"]

if TYPE_CHECKING:
    from .base import BaseClient


class DashboardsClient:
    """Client for dashboard-related API calls."""

    def __init__(self, client: BaseClient):
        self._client = client

    def list(self, collection_id: int | None = None) -> list[dict[str, Any]]:
        """List dashboards with optional collection filtering.

        Uses the search API with models=dashboard filter.

        Args:
            collection_id: Optional collection ID to filter by.

        Returns:
            List of dashboard dictionaries.
        """
        params: dict[str, Any] = {
            "models": "dashboard",
        }

        if collection_id is not None:
            params["collection_id"] = collection_id

        response = self._client.get("/search", params=params)

        # The API returns {"data": [...]}
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return []

    def get(self, dashboard_id: int) -> dict[str, Any]:
        """Get dashboard with all dashcard definitions.

        Makes a GET request to /api/dashboard/:id.

        Args:
            dashboard_id: The ID of the dashboard to retrieve.

        Returns:
            Dashboard dictionary with full details including dashcards.
        """
        return self._client.get(f"/dashboard/{dashboard_id}")

    def create(self, dashboard_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new dashboard.

        Makes a POST request to /api/dashboard/.

        Args:
            dashboard_data: Dashboard definition dict containing at least name.

        Returns:
            Created dashboard dictionary.
        """
        return self._client.post("/dashboard", json=dashboard_data)

    def update(self, dashboard_id: int, dashboard_data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing dashboard.

        Makes a PUT request to /api/dashboard/:id.

        Args:
            dashboard_id: The ID of the dashboard to update.
            dashboard_data: Dashboard fields to update.

        Returns:
            Updated dashboard dictionary.
        """
        return self._client.put(f"/dashboard/{dashboard_id}", json=dashboard_data)

    def archive(self, dashboard_id: int) -> dict[str, Any]:
        """Archive a dashboard (soft delete).

        Makes a PUT request to /api/dashboard/:id with archived=true.

        Args:
            dashboard_id: The ID of the dashboard to archive.

        Returns:
            Updated dashboard dictionary.
        """
        return self._client.put(f"/dashboard/{dashboard_id}", json={"archived": True})

    def delete(self, dashboard_id: int) -> None:
        """Permanently delete a dashboard.

        Makes a DELETE request to /api/dashboard/:id.

        Args:
            dashboard_id: The ID of the dashboard to delete.
        """
        self._client.delete(f"/dashboard/{dashboard_id}")

    def list_revisions(self, dashboard_id: int) -> list[dict[str, Any]]:
        """List dashboard revisions.

        Makes a GET request to /api/dashboard/:id/revisions.

        Args:
            dashboard_id: The ID of the dashboard.

        Returns:
            List of revision dictionaries.
        """
        response = self._client.get(f"/dashboard/{dashboard_id}/revisions")

        # The API returns a list directly
        if isinstance(response, list):
            return response
        return []

    def revert(self, dashboard_id: int, revision_id: int) -> dict[str, Any]:
        """Revert dashboard to a previous revision.

        Makes a POST request to /api/dashboard/:id/revert.

        Args:
            dashboard_id: The ID of the dashboard.
            revision_id: The revision ID to revert to.

        Returns:
            Reverted dashboard dictionary.
        """
        return self._client.post(
            f"/dashboard/{dashboard_id}/revert",
            json={"revision_id": revision_id},
        )
