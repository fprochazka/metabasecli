"""Metabase data models.

This module contains dataclasses representing Metabase entities.
Models are simple data containers with no business logic.
"""

from .auth import AuthConfig, AuthMethod, SessionInfo
from .card import Card, CardQuery, VisualizationSettings
from .collection import Collection, CollectionItem
from .dashboard import Dashboard, DashCard
from .database import Database, Field, Table

__all__ = [
    # Auth
    "AuthConfig",
    "AuthMethod",
    "SessionInfo",
    # Database
    "Database",
    "Table",
    "Field",
    # Collection
    "Collection",
    "CollectionItem",
    # Card
    "Card",
    "CardQuery",
    "VisualizationSettings",
    # Dashboard
    "Dashboard",
    "DashCard",
]
