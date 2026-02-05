"""Collection commands.

Provides commands for managing Metabase collections, including listing,
creating, updating, and archiving collections.
"""

from typing import Annotated

import typer

from ..logging import error_console

app = typer.Typer(name="collections", help="Collection operations.")


@app.command("tree")
def tree(
    search: Annotated[
        str | None,
        typer.Option("--search", help="Filter collections by name."),
    ] = None,
    levels: Annotated[
        int,
        typer.Option("--levels", help="How many levels deep to render from matched results."),
    ] = 1,
    exclude_archived: Annotated[
        bool,
        typer.Option("--exclude-archived/--include-archived", help="Exclude archived collections."),
    ] = True,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Display collection hierarchy as a tree."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("get")
def get_collection(
    collection_id: Annotated[str, typer.Argument(help="Collection ID or 'root'.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Get collection details."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("items")
def list_items(
    collection_id: Annotated[str, typer.Argument(help="Collection ID or 'root'.")],
    models: Annotated[
        str | None,
        typer.Option("--models", help="Filter by type: card, dashboard, collection, dataset, pulse."),
    ] = None,
    archived: Annotated[
        bool,
        typer.Option("--archived", help="Show archived items."),
    ] = False,
    sort_by: Annotated[
        str | None,
        typer.Option("--sort-by", help="Sort by: name, last_edited_at, last_edited_by, model."),
    ] = None,
    sort_dir: Annotated[
        str | None,
        typer.Option("--sort-dir", help="Sort direction: asc, desc."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List items in a collection."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("create")
def create_collection(
    name: Annotated[
        str,
        typer.Option("--name", help="Collection name."),
    ],
    description: Annotated[
        str | None,
        typer.Option("--description", help="Description."),
    ] = None,
    parent_id: Annotated[
        int | None,
        typer.Option("--parent-id", help="Parent collection ID."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Create a new collection."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("update")
def update_collection(
    collection_id: Annotated[int, typer.Argument(help="Collection ID.")],
    name: Annotated[
        str | None,
        typer.Option("--name", help="New name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description."),
    ] = None,
    parent_id: Annotated[
        int | None,
        typer.Option("--parent-id", help="Move to new parent."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Update a collection."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("archive")
def archive_collection(
    collection_id: Annotated[int, typer.Argument(help="Collection ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Archive a collection."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)
