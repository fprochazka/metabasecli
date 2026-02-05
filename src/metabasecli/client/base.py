"""Base client with session management and request helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from .auth import AuthClient
    from .cards import CardsClient
    from .collections import CollectionsClient
    from .dashboards import DashboardsClient
    from .databases import DatabasesClient

from ..models.auth import AuthConfig, AuthMethod


class MetabaseAPIError(Exception):
    """Raised when the Metabase API returns an error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class AuthenticationError(MetabaseAPIError):
    """Raised when authentication fails."""

    pass


class NotFoundError(MetabaseAPIError):
    """Raised when a resource is not found."""

    pass


class BaseClient:
    """Base HTTP client with session management."""

    def __init__(self, config: AuthConfig):
        self.config = config
        self._client: httpx.Client | None = None

    @property
    def base_url(self) -> str:
        """Get the base URL for API requests."""
        return f"{self.config.url.rstrip('/')}/api"

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers based on auth method."""
        if self.config.auth_method == AuthMethod.API_KEY:
            if not self.config.api_key:
                raise AuthenticationError("API key not configured")
            return {"x-api-key": self.config.api_key}

        if self.config.auth_method in (AuthMethod.SESSION_ID, AuthMethod.CREDENTIALS):
            if not self.config.session_id:
                raise AuthenticationError("Session ID not available")
            return {"x-metabase-session": self.config.session_id}

        raise AuthenticationError(f"Unknown auth method: {self.config.auth_method}")

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "Content-Type": "application/json",
                    **self._get_auth_headers(),
                },
                timeout=30.0,
            )
        return self._client

    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle API response, raising appropriate errors."""
        if response.status_code == 401:
            raise AuthenticationError(
                "Authentication failed",
                status_code=401,
                response=response.json() if response.content else None,
            )

        if response.status_code == 404:
            raise NotFoundError(
                "Resource not found",
                status_code=404,
                response=response.json() if response.content else None,
            )

        if response.status_code >= 400:
            error_data = response.json() if response.content else {}
            message = error_data.get("message", f"API error: {response.status_code}")
            raise MetabaseAPIError(
                message,
                status_code=response.status_code,
                response=error_data,
            )

        if not response.content:
            return None

        return response.json()

    def get(self, path: str, params: dict | None = None) -> Any:
        """Make a GET request."""
        client = self._get_client()
        response = client.get(path, params=params)
        return self._handle_response(response)

    def post(self, path: str, json: dict | None = None) -> Any:
        """Make a POST request."""
        client = self._get_client()
        response = client.post(path, json=json)
        return self._handle_response(response)

    def put(self, path: str, json: dict | None = None) -> Any:
        """Make a PUT request."""
        client = self._get_client()
        response = client.put(path, json=json)
        return self._handle_response(response)

    def delete(self, path: str) -> Any:
        """Make a DELETE request."""
        client = self._get_client()
        response = client.delete(path)
        return self._handle_response(response)

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None


class MetabaseClient(BaseClient):
    """Main Metabase API client combining all resource clients.

    This is the primary entry point for API interactions.
    Individual resource clients (auth, databases, etc.) are lazily initialized.
    """

    def __init__(self, config: AuthConfig):
        super().__init__(config)
        self._auth: AuthClient | None = None
        self._databases: DatabasesClient | None = None
        self._collections: CollectionsClient | None = None
        self._cards: CardsClient | None = None
        self._dashboards: DashboardsClient | None = None

    @property
    def auth(self) -> AuthClient:
        """Get the auth client."""
        if self._auth is None:
            from .auth import AuthClient

            self._auth = AuthClient(self)
        return self._auth

    @property
    def databases(self) -> DatabasesClient:
        """Get the databases client."""
        if self._databases is None:
            from .databases import DatabasesClient

            self._databases = DatabasesClient(self)
        return self._databases

    @property
    def collections(self) -> CollectionsClient:
        """Get the collections client."""
        if self._collections is None:
            from .collections import CollectionsClient

            self._collections = CollectionsClient(self)
        return self._collections

    @property
    def cards(self) -> CardsClient:
        """Get the cards client."""
        if self._cards is None:
            from .cards import CardsClient

            self._cards = CardsClient(self)
        return self._cards

    @property
    def dashboards(self) -> DashboardsClient:
        """Get the dashboards client."""
        if self._dashboards is None:
            from .dashboards import DashboardsClient

            self._dashboards = DashboardsClient(self)
        return self._dashboards
