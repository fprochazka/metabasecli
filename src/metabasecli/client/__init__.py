"""Metabase API client.

This module contains the HTTP client for interacting with the Metabase API.
"""

from .auth import AuthClient
from .base import BaseClient, MetabaseClient
from .cards import CardsClient
from .collections import CollectionsClient
from .dashboards import DashboardsClient
from .databases import DatabasesClient
from .search import SearchClient

__all__ = [
    "BaseClient",
    "MetabaseClient",
    "AuthClient",
    "DatabasesClient",
    "CollectionsClient",
    "CardsClient",
    "DashboardsClient",
    "SearchClient",
]
