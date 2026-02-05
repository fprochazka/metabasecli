from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import MetabaseClient
    from .models.auth import AuthConfig


@dataclass
class Context:
    """CLI context passed to all commands."""

    verbose: bool = False
    profile: str = "default"
    _config: "AuthConfig | None" = field(default=None, repr=False)
    _client: "MetabaseClient | None" = field(default=None, repr=False)

    @property
    def config(self) -> "AuthConfig | None":
        """Get the current configuration, loading from file/env if needed."""
        if self._config is None:
            from .config import load_config

            self._config = load_config(self.profile)
        return self._config

    @config.setter
    def config(self, value: "AuthConfig | None") -> None:
        """Set the configuration and reset the client."""
        self._config = value
        self._client = None

    @property
    def client(self) -> "MetabaseClient":
        """Get the Metabase client.

        Raises:
            RuntimeError: If no configuration is available.
        """
        if self._client is None:
            config = self.config
            if config is None:
                raise RuntimeError("Not authenticated. Run 'metabase auth login' first or set environment variables.")

            from .client import MetabaseClient

            self._client = MetabaseClient(config)
        return self._client

    def require_auth(self) -> "MetabaseClient":
        """Get the client, raising an error if not authenticated.

        This is an alias for the client property with a clearer name
        for use in commands.
        """
        return self.client


_ctx = Context()


def get_context() -> Context:
    return _ctx
