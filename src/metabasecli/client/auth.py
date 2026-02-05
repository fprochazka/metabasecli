"""Authentication-related API calls."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import BaseClient


class AuthClient:
    """Client for authentication-related API calls."""

    def __init__(self, client: "BaseClient"):
        self._client = client

    def login(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate with username and password.

        Returns session information including the session_id.
        """
        # Note: This doesn't use _get_auth_headers since we're authenticating
        raise NotImplementedError("Auth login not implemented")

    def logout(self) -> None:
        """Invalidate the current session."""
        raise NotImplementedError("Auth logout not implemented")

    def get_current_user(self) -> dict[str, Any]:
        """Get information about the currently authenticated user."""
        raise NotImplementedError("Get current user not implemented")

    def validate_session(self) -> bool:
        """Check if the current session is valid."""
        raise NotImplementedError("Validate session not implemented")
