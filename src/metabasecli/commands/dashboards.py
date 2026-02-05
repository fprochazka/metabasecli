"""Dashboard commands."""

from typing import Annotated

import typer

from ..logging import error_console

app = typer.Typer(name="dashboards", help="Dashboard operations.")


@app.command("list")
def list_dashboards(
    collection_id: Annotated[
        int | None,
        typer.Option("--collection-id", help="Filter by collection."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List all dashboards."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("get")
def get_dashboard(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID.")],
    include_cards: Annotated[
        bool,
        typer.Option("--include-cards", help="Include full card definitions."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Get dashboard with all dashcard definitions."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("export")
def export_dashboard(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Return file paths as JSON."),
    ] = False,
) -> None:
    """Export a complete dashboard with all referenced cards."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("import")
def import_dashboard(
    file: Annotated[
        str | None,
        typer.Option("--file", help="Path to manifest.json or dashboard JSON file."),
    ] = None,
    dashboard_id: Annotated[
        int | None,
        typer.Option("--id", help="Dashboard ID to update (if omitted, creates new)."),
    ] = None,
    collection_id: Annotated[
        int | None,
        typer.Option("--collection-id", help="Target collection."),
    ] = None,
    database_id: Annotated[
        int | None,
        typer.Option("--database-id", help="Target database for cards."),
    ] = None,
    cards_only: Annotated[
        bool,
        typer.Option("--cards-only", help="Only import/update cards, skip dashboard."),
    ] = False,
    dashboard_only: Annotated[
        bool,
        typer.Option("--dashboard-only", help="Only import/update dashboard, assume cards exist."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be imported without making changes."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Import a dashboard from a JSON definition file."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("archive")
def archive_dashboard(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Archive a dashboard (soft delete)."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("delete")
def delete_dashboard(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID.")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Permanently delete a dashboard."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("revisions")
def list_revisions(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List dashboard revisions."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)


@app.command("revert")
def revert_dashboard(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID.")],
    revision_id: Annotated[int, typer.Argument(help="Revision ID to revert to.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Revert dashboard to a previous revision."""
    error_console.print("[yellow]Not implemented yet[/yellow]")
    raise typer.Exit(1)
