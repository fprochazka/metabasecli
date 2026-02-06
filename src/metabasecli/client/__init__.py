"""Metabase API client.

This module contains the HTTP client for interacting with the Metabase API.
"""

from .auth import AuthClient
from .base import (
    AuthenticationError,
    BaseClient,
    MetabaseAPIError,
    MetabaseClient,
    NotFoundError,
    PermissionDeniedError,
    SessionExpiredError,
)
from .cards import CardsClient
from .collections import CollectionsClient
from .dashboards import DashboardsClient
from .databases import DatabasesClient
from .search import SearchClient

__all__ = [
    "MetabaseAPIError",
    "AuthenticationError",
    "NotFoundError",
    "SessionExpiredError",
    "PermissionDeniedError",
    "BaseClient",
    "MetabaseClient",
    "AuthClient",
    "DatabasesClient",
    "CollectionsClient",
    "CardsClient",
    "DashboardsClient",
    "SearchClient",
]
