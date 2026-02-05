"""Authentication-related models.

Contains dataclasses for authentication configuration and session information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

__all__ = ["AuthMethod", "AuthConfig", "SessionInfo"]


class AuthMethod(StrEnum):
    """Supported authentication methods."""

    API_KEY = "api_key"
    SESSION_ID = "session_id"
    CREDENTIALS = "credentials"


@dataclass
class AuthConfig:
    """Authentication configuration."""

    url: str
    auth_method: AuthMethod
    profile: str = "default"

    # For API key auth
    api_key: str | None = None

    # For session ID auth
    session_id: str | None = None

    # For credentials auth
    username: str | None = None
    password: str | None = None


@dataclass
class SessionInfo:
    """Information about the current session."""

    authenticated: bool
    auth_method: AuthMethod | None = None
    user_id: int | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_superuser: bool = False
    instance_url: str | None = None
    session_expires: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)
