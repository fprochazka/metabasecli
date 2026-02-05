"""Database commands."""

from typing import Annotated

import typer

from ..logging import error_console

app = typer.Typer(name="databases", help="Database operations.")


@app.command("list")
def list_databases(
    include_tables: Annotated[
        bool,
        typer.Option("--include-tables", help="Include table information."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List all databases."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("get")
def get_database(
    database_id: Annotated[int, typer.Argument(help="Database ID.")],
    include_tables: Annotated[
        bool,
        typer.Option("--include-tables", help="Include tables."),
    ] = False,
    include_fields: Annotated[
        bool,
        typer.Option("--include-fields", help="Include tables and fields."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Get database details."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("metadata")
def get_metadata(
    database_id: Annotated[int, typer.Argument(help="Database ID.")],
    include_hidden: Annotated[
        bool,
        typer.Option("--include-hidden", help="Include hidden tables and fields."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Get complete database metadata including all tables and fields."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("schemas")
def list_schemas(
    database_id: Annotated[int, typer.Argument(help="Database ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List all schemas in a database."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)
