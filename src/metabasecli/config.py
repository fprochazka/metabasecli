"""Configuration management for the Metabase CLI.

Handles loading and saving configuration from ~/.config/metabasecli/config.toml
"""

import os
from pathlib import Path

from .models.auth import AuthConfig, AuthMethod

__all__ = [
    "ConfigError",
    "get_config_path",
    "ensure_config_dir",
    "load_config",
    "save_config",
    "update_session_id",
]

# Default config directory
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "metabasecli"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.toml"

# Environment variable names
ENV_URL = "METABASE_URL"
ENV_API_KEY = "METABASE_API_KEY"
ENV_SESSION_ID = "METABASE_SESSION_ID"
ENV_USERNAME = "METABASE_USERNAME"
ENV_PASSWORD = "METABASE_PASSWORD"


class ConfigError(Exception):
    """Raised when there's a configuration error."""


def get_config_path() -> Path:
    """Get the path to the config file."""
    return DEFAULT_CONFIG_FILE


def ensure_config_dir() -> Path:
    """Ensure the config directory exists."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_DIR


def load_config(profile: str = "default") -> AuthConfig | None:
    """Load configuration from file and environment.

    Environment variables take precedence over file configuration.

    Args:
        profile: The profile name to load from the config file.

    Returns:
        AuthConfig if configuration is available, None otherwise.
    """
    # Start with file configuration
    file_config = _load_file_config(profile)

    # Override with environment variables
    config = _apply_env_overrides(file_config)

    return config


def _load_file_config(profile: str) -> dict:
    """Load configuration from the TOML file."""
    config_path = get_config_path()

    if not config_path.exists():
        return {}

    try:
        import tomllib

        with open(config_path, "rb") as f:
            all_config = tomllib.load(f)
            return all_config.get(profile, {})
    except ImportError:
        # Python < 3.11 fallback
        import tomli

        with open(config_path, "rb") as f:
            all_config = tomli.load(f)
            return all_config.get(profile, {})
    except Exception as e:
        raise ConfigError(f"Failed to load config file: {e}") from e


def _apply_env_overrides(file_config: dict) -> AuthConfig | None:
    """Apply environment variable overrides to file configuration."""
    # Get URL
    url = os.environ.get(ENV_URL, file_config.get("url"))
    if not url:
        return None

    # Determine auth method from environment or file
    api_key = os.environ.get(ENV_API_KEY, file_config.get("api_key"))
    session_id = os.environ.get(ENV_SESSION_ID, file_config.get("session_id"))
    username = os.environ.get(ENV_USERNAME, file_config.get("username"))
    password = os.environ.get(ENV_PASSWORD, file_config.get("password"))

    # Determine auth method
    if api_key:
        auth_method = AuthMethod.API_KEY
    elif username and password:
        auth_method = AuthMethod.CREDENTIALS
    elif session_id:
        auth_method = AuthMethod.SESSION_ID
    else:
        # Check file config for explicit auth_method
        file_method = file_config.get("auth_method")
        if file_method:
            auth_method = AuthMethod(file_method)
        else:
            return None

    return AuthConfig(
        url=url,
        auth_method=auth_method,
        api_key=api_key,
        session_id=session_id,
        username=username,
        password=password,
    )


def save_config(config: AuthConfig, profile: str = "default") -> None:
    """Save configuration to the TOML file.

    Args:
        config: The configuration to save.
        profile: The profile name to save to.
    """
    ensure_config_dir()
    config_path = get_config_path()

    # Load existing config
    existing = {}
    if config_path.exists():
        try:
            import tomllib

            with open(config_path, "rb") as f:
                existing = tomllib.load(f)
        except ImportError:
            import tomli

            with open(config_path, "rb") as f:
                existing = tomli.load(f)

    # Update profile
    profile_config = {
        "url": config.url,
        "auth_method": config.auth_method.value,
    }

    if config.api_key:
        profile_config["api_key"] = config.api_key
    if config.session_id:
        profile_config["session_id"] = config.session_id
    if config.username:
        profile_config["username"] = config.username
    if config.password:
        profile_config["password"] = config.password

    existing[profile] = profile_config

    # Write back
    _write_toml(config_path, existing)


def _write_toml(path: Path, data: dict) -> None:
    """Write data to a TOML file."""
    lines = []
    for section, values in data.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            if isinstance(value, str):
                lines.append(f'{key} = "{value}"')
            elif isinstance(value, bool):
                lines.append(f"{key} = {str(value).lower()}")
            else:
                lines.append(f"{key} = {value}")
        lines.append("")

    path.write_text("\n".join(lines))


def update_session_id(session_id: str, profile: str = "default") -> None:
    """Update just the session_id in the config file.

    This is used for auto-refresh of session tokens.
    """
    config = load_config(profile)
    if config:
        config.session_id = session_id
        save_config(config, profile)
