"""Search command."""

from typing import Annotated

import typer

from ..logging import error_console


def search_command(
    query: Annotated[str, typer.Argument(help="Search term.")],
    models: Annotated[
        str | None,
        typer.Option(
            "--models",
            help="Filter by type: card, dashboard, collection, database, table, dataset, segment, metric, action.",
        ),
    ] = None,
    collection_id: Annotated[
        int | None,
        typer.Option("--collection-id", help="Search within collection."),
    ] = None,
    database_id: Annotated[
        int | None,
        typer.Option("--database-id", help="Filter by database."),
    ] = None,
    archived: Annotated[
        bool,
        typer.Option("--archived", help="Search archived items."),
    ] = False,
    created_by: Annotated[
        int | None,
        typer.Option("--created-by", help="Filter by creator user ID."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Max results."),
    ] = 50,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Global search across all Metabase entities."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)
