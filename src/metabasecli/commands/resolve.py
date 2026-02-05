"""Resolve command for parsing Metabase URLs."""

from typing import Annotated

import typer

from ..logging import error_console


def resolve_command(
    url: Annotated[str, typer.Argument(help="Metabase URL (full URL or path only).")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Parse a Metabase URL and return information about the referenced entity."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)
