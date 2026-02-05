"""Authentication commands."""

from typing import Annotated

import typer

from ..logging import error_console

app = typer.Typer(name="auth", help="Authentication commands.")


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
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("logout")
def logout(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Profile to clear."),
    ] = "default",
) -> None:
    """Clear stored session."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


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
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("token")
def token(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Profile to use."),
    ] = "default",
) -> None:
    """Print current session token (for piping)."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)
