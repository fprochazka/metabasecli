"""Card (saved question) commands."""

from typing import Annotated

import typer

from ..logging import error_console

app = typer.Typer(name="cards", help="Card/query operations.")


@app.command("list")
def list_cards(
    filter_type: Annotated[
        str | None,
        typer.Option(
            "--filter",
            help="Filter: all, mine, bookmarked, archived, database, table, using_model.",
        ),
    ] = None,
    collection_id: Annotated[
        int | None,
        typer.Option("--collection-id", help="Filter by collection."),
    ] = None,
    database_id: Annotated[
        int | None,
        typer.Option("--database-id", help="Filter by database (requires --filter=database)."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List all cards."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("get")
def get_card(
    card_id: Annotated[int, typer.Argument(help="Card ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Get card details including full query definition."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("run")
def run_card(
    card_id: Annotated[int, typer.Argument(help="Card ID.")],
    parameters: Annotated[
        str | None,
        typer.Option("--parameters", help="Query parameters as JSON."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Limit rows."),
    ] = 2000,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Execute a card's query and return results."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("import")
def import_card(
    file: Annotated[
        str | None,
        typer.Option("--file", help="Path to card JSON file (or use stdin)."),
    ] = None,
    card_id: Annotated[
        int | None,
        typer.Option("--id", help="Card ID to update (if omitted, creates new card)."),
    ] = None,
    collection_id: Annotated[
        int | None,
        typer.Option("--collection-id", help="Target collection (overrides file)."),
    ] = None,
    database_id: Annotated[
        int | None,
        typer.Option("--database-id", help="Target database (overrides file)."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Import a card from a JSON definition file."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("archive")
def archive_card(
    card_id: Annotated[int, typer.Argument(help="Card ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Archive a card (soft delete)."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("delete")
def delete_card(
    card_id: Annotated[int, typer.Argument(help="Card ID.")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Permanently delete a card."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)
