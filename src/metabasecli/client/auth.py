"""Authentication-related API calls."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from .base import BaseClient


class AuthClient:
    """Client for authentication-related API calls."""

    def __init__(self, client: BaseClient):
        self._client = client

    def login(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate with username and password.

        Makes a POST request to /api/session to obtain a session ID.
        This does not use _get_auth_headers since we're authenticating.

        Returns:
            Session response including the session_id.
        """
        # Create a temporary client without auth headers for login
        response = httpx.post(
            f"{self._client.base_url}/session",
            json={"username": username, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )
        return self._client._handle_response(response)

    def logout(self, session_id: str) -> None:
        """Invalidate the specified session.

        Makes a DELETE request to /api/session.

        Args:
            session_id: The session ID to invalidate.
        """
        response = httpx.delete(
            f"{self._client.base_url}/session",
            headers={
                "Content-Type": "application/json",
                "x-metabase-session": session_id,
            },
            timeout=30.0,
        )
        # Ignore 401 errors during logout (session already invalid)
        if response.status_code not in (200, 204, 401):
            self._client._handle_response(response)

    def get_session_properties(self) -> dict[str, Any]:
        """Get properties of the current session.

        Makes a GET request to /api/session/properties.
        This validates the session and returns user information.

        Returns:
            Session properties including user info.
        """
        return self._client.get("/session/properties")

    def get_current_user(self) -> dict[str, Any]:
        """Get information about the currently authenticated user.

        Makes a GET request to /api/user/current.

        Returns:
            Current user information.
        """
        return self._client.get("/user/current")

    def validate_session(self) -> bool:
        """Check if the current session is valid.

        Returns:
            True if the session is valid, False otherwise.
        """
        try:
            self.get_session_properties()
            return True
        except Exception:
            return False
