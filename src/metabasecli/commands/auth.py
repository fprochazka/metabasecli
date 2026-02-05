"""Authentication commands."""

from typing import Annotated

import typer

from ..client.base import AuthenticationError
from ..config import load_config, save_config
from ..context import get_context
from ..logging import console, error_console
from ..models.auth import AuthConfig, AuthMethod
from ..output import output_error_json, output_json

app = typer.Typer(name="auth", help="Authentication commands.")


def _prompt_auth_method() -> AuthMethod:
    """Prompt user to select an authentication method."""
    console.print("\n[bold]Select authentication method:[/bold]")
    console.print("  [cyan]1[/cyan]. api_key     - Use a Metabase API key")
    console.print("  [cyan]2[/cyan]. session_id  - Use an existing session ID")
    console.print("  [cyan]3[/cyan]. credentials - Use username and password")
    console.print()

    choice = typer.prompt("Enter choice (1-3)", default="1")

    method_map = {
        "1": AuthMethod.API_KEY,
        "2": AuthMethod.SESSION_ID,
        "3": AuthMethod.CREDENTIALS,
        "api_key": AuthMethod.API_KEY,
        "session_id": AuthMethod.SESSION_ID,
        "credentials": AuthMethod.CREDENTIALS,
    }

    method = method_map.get(choice.lower())
    if not method:
        error_console.print(f"[red]Invalid choice: {choice}[/red]")
        raise typer.Exit(1)

    return method


def _validate_url(url: str) -> str:
    """Validate and normalize the Metabase URL."""
    # Ensure it starts with http:// or https://
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Remove trailing slash
    return url.rstrip("/")


@app.command("login")
def login(
    url: Annotated[
        str | None,
        typer.Option("--url", help="Metabase instance URL."),
    ] = None,
    method: Annotated[
        str | None,
        typer.Option(
            "--method",
            help="Auth method: api_key, session_id, or credentials.",
        ),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Profile name for storing credentials."),
    ] = "default",
) -> None:
    """Authenticate with Metabase and store credentials."""
    # Get URL
    if not url:
        url = typer.prompt("Metabase URL")
    url = _validate_url(url)

    # Get auth method
    if method:
        method_map = {
            "api_key": AuthMethod.API_KEY,
            "session_id": AuthMethod.SESSION_ID,
            "credentials": AuthMethod.CREDENTIALS,
        }
        auth_method = method_map.get(method.lower())
        if not auth_method:
            error_console.print(f"[red]Invalid auth method: {method}. Use api_key, session_id, or credentials.[/red]")
            raise typer.Exit(1)
    else:
        auth_method = _prompt_auth_method()

    # Collect auth-specific information
    config = AuthConfig(
        url=url,
        auth_method=auth_method,
        profile=profile,
    )

    if auth_method == AuthMethod.API_KEY:
        api_key = typer.prompt("API Key", hide_input=True)
        config.api_key = api_key

        # Validate the API key by making a test request
        console.print("\n[dim]Validating API key...[/dim]")
        try:
            from ..client.base import MetabaseClient

            client = MetabaseClient(config)
            client.auth.get_session_properties()
            console.print("[green]API key is valid![/green]")
        except AuthenticationError:
            error_console.print("[red]Invalid API key[/red]")
            raise typer.Exit(1) from None
        except Exception as e:
            error_console.print(f"[red]Failed to validate API key: {e}[/red]")
            raise typer.Exit(1) from None

    elif auth_method == AuthMethod.SESSION_ID:
        session_id = typer.prompt("Session ID", hide_input=True)
        config.session_id = session_id

        # Validate the session ID
        console.print("\n[dim]Validating session ID...[/dim]")
        try:
            from ..client.base import MetabaseClient

            client = MetabaseClient(config)
            client.auth.get_session_properties()
            console.print("[green]Session ID is valid![/green]")
        except AuthenticationError:
            error_console.print("[red]Invalid or expired session ID[/red]")
            raise typer.Exit(1) from None
        except Exception as e:
            error_console.print(f"[red]Failed to validate session ID: {e}[/red]")
            raise typer.Exit(1) from None

    elif auth_method == AuthMethod.CREDENTIALS:
        username = typer.prompt("Username (email)")
        password = typer.prompt("Password", hide_input=True)
        config.username = username
        config.password = password

        # Authenticate to get a session ID
        console.print("\n[dim]Authenticating...[/dim]")
        try:
            from ..client.base import MetabaseClient

            # Create a temporary config without session to perform login
            temp_config = AuthConfig(
                url=url,
                auth_method=AuthMethod.CREDENTIALS,
                profile=profile,
            )
            client = MetabaseClient(temp_config)
            session_response = client.auth.login(username, password)
            session_id = session_response.get("id")
            if not session_id:
                error_console.print("[red]No session ID in response[/red]")
                raise typer.Exit(1)

            config.session_id = session_id
            console.print("[green]Authentication successful![/green]")
        except AuthenticationError as e:
            error_console.print(f"[red]Authentication failed: {e}[/red]")
            raise typer.Exit(1) from None
        except Exception as e:
            error_console.print(f"[red]Failed to authenticate: {e}[/red]")
            raise typer.Exit(1) from None

    # Save configuration
    save_config(config, profile)

    from ..config import get_config_path

    console.print(f"\n[green]Session saved to {get_config_path()}[/green]")
    console.print(f"[dim]Profile: {profile}[/dim]")


@app.command("logout")
def logout(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Profile to clear."),
    ] = "default",
) -> None:
    """Clear stored session."""
    # Load current config
    config = load_config(profile)

    if config is None:
        console.print("[yellow]No configuration found for this profile.[/yellow]")
        return

    # If we have a session ID, invalidate it on the server
    if config.session_id and config.auth_method in (
        AuthMethod.SESSION_ID,
        AuthMethod.CREDENTIALS,
    ):
        console.print("[dim]Invalidating session on server...[/dim]")
        try:
            from ..client.base import MetabaseClient

            client = MetabaseClient(config)
            client.auth.logout(config.session_id)
            console.print("[green]Session invalidated on server.[/green]")
        except Exception:
            # Ignore errors during logout - the session might already be invalid
            console.print("[dim]Could not invalidate session on server (may already be expired).[/dim]")

    # Clear config file for this profile
    from ..config import get_config_path

    config_path = get_config_path()
    if config_path.exists():
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(config_path, "rb") as f:
            all_config = tomllib.load(f)

        # Remove the profile
        if profile in all_config:
            del all_config[profile]

            # Write back
            from ..config import _write_toml

            if all_config:
                _write_toml(config_path, all_config)
            else:
                # Remove the file if no profiles left
                config_path.unlink()

            console.print(f"[green]Profile '{profile}' has been removed.[/green]")
        else:
            console.print(f"[yellow]Profile '{profile}' not found in config file.[/yellow]")
    else:
        console.print("[yellow]No config file found.[/yellow]")


@app.command("status")
def status(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Profile to check."),
    ] = "default",
) -> None:
    """Show current authentication status."""
    ctx = get_context()
    ctx.profile = profile

    config = load_config(profile)

    if config is None:
        if json_output:
            output_json({"authenticated": False}, success=True)
        else:
            console.print("[yellow]Not authenticated.[/yellow]")
            console.print("[dim]Run 'metabase auth login' to authenticate.[/dim]")
        return

    # Try to get session info
    try:
        from ..client.base import MetabaseClient

        client = MetabaseClient(config)
        client.auth.get_session_properties()
        user_info = client.auth.get_current_user()

        if json_output:
            output_json(
                {
                    "authenticated": True,
                    "auth_method": config.auth_method.value,
                    "user": {
                        "id": user_info.get("id"),
                        "email": user_info.get("email"),
                        "first_name": user_info.get("first_name"),
                        "last_name": user_info.get("last_name"),
                        "is_superuser": user_info.get("is_superuser", False),
                    },
                    "instance_url": config.url,
                }
            )
        else:
            console.print(f"[green]Authenticated as:[/green] {user_info.get('email', 'Unknown')}")
            name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
            if name:
                console.print(f"[green]Name:[/green] {name}")
            console.print(f"[green]Instance:[/green] {config.url}")
            console.print(f"[green]Auth method:[/green] {config.auth_method.value}")
            if user_info.get("is_superuser"):
                console.print("[cyan]User is a superuser[/cyan]")

    except AuthenticationError:
        if json_output:
            output_json(
                {
                    "authenticated": False,
                    "auth_method": config.auth_method.value,
                    "instance_url": config.url,
                    "error": "Session expired or invalid",
                }
            )
        else:
            console.print("[red]Session expired or invalid.[/red]")
            console.print(f"[dim]Instance: {config.url}[/dim]")
            console.print(f"[dim]Auth method: {config.auth_method.value}[/dim]")
            console.print("[dim]Run 'metabase auth login' to re-authenticate.[/dim]")
        raise typer.Exit(1) from None

    except Exception as e:
        if json_output:
            output_error_json(
                code="API_ERROR",
                message=str(e),
            )
        else:
            error_console.print(f"[red]Error checking status: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("token")
def token(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Profile to use."),
    ] = "default",
) -> None:
    """Print current session token (for piping)."""
    config = load_config(profile)

    if config is None:
        error_console.print("[red]Not authenticated. Run 'metabase auth login' first.[/red]")
        raise typer.Exit(1)

    # Print the appropriate token based on auth method
    if config.auth_method == AuthMethod.API_KEY:
        if config.api_key:
            print(config.api_key)
        else:
            error_console.print("[red]No API key configured.[/red]")
            raise typer.Exit(1)
    else:
        if config.session_id:
            print(config.session_id)
        else:
            error_console.print("[red]No session ID available.[/red]")
            raise typer.Exit(1)
