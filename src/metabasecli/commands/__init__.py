"""Command modules for the Metabase CLI.

Each module defines a typer app for a command group.
"""

from .auth import app as auth_app
from .cards import app as cards_app
from .collections import app as collections_app
from .dashboards import app as dashboards_app
from .databases import app as databases_app
from .resolve import resolve_command
from .search import search_command

__all__ = [
    "auth_app",
    "databases_app",
    "collections_app",
    "cards_app",
    "dashboards_app",
    "search_command",
    "resolve_command",
]
