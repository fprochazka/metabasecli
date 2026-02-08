"""Dashboard commands.

Provides commands for managing Metabase dashboards including listing, viewing,
exporting/importing, revisions, and archiving/deleting dashboards.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from ..client.base import NotFoundError
from ..constants import EXPORT_VERSION
from ..context import get_context
from ..logging import console, error_console
from ..models.dashboard import Dashboard
from ..output import (
    create_export_dir,
    get_collection_path_parts,
    handle_api_error,
    output_error_json,
    output_json,
    write_export_file,
    write_json_file,
)

app = typer.Typer(name="dashboards", help="Dashboard operations.")

# Fields allowed in each dashcard when sending to PUT /api/dashboard/:id
_DASHCARD_ALLOWED_FIELDS = {
    "card_id",
    "row",
    "col",
    "size_x",
    "size_y",
    "parameter_mappings",
    "visualization_settings",
    "series",
    "dashboard_tab_id",
}

# Read-only fields that must be stripped from dashboard data before create/update.
# Note: ``ordered_cards`` is NOT listed here because it must remain available for
# ``_prepare_dashcards_for_import`` to read from; it is removed explicitly after
# dashcards have been prepared.
_DASHBOARD_READONLY_FIELDS = [
    "id",
    "creator_id",
    "creator",
    "created_at",
    "updated_at",
    "made_public_by_id",
    "public_uuid",
    "entity_id",
    "collection",
    "embedding_params",
    "param_fields",
    "param_values",
    "last-edit-info",
    "can_write",
]


def _prepare_dashcards_for_import(
    dashboard_data: dict[str, Any],
    card_id_mapping: dict[int, int] | None = None,
) -> list[dict[str, Any]]:
    """Prepare dashcards for import by cleaning and assigning negative IDs.

    The Metabase PUT /api/dashboard/:id endpoint requires:
    - Dashcards under the ``dashcards`` key (not ``ordered_cards``)
    - Negative IDs for new dashcard placements
    - Only whitelisted fields per dashcard (no embedded ``card`` object, etc.)

    Args:
        dashboard_data: Raw dashboard data dict (from GET response or export file).
            Dashcards are read from either ``ordered_cards`` or ``dashcards`` key.
        card_id_mapping: Optional mapping from old card IDs to new card IDs.
            Used when cards were created during import and received new IDs.

    Returns:
        List of cleaned dashcard dicts ready for the API.
    """
    raw_dashcards = dashboard_data.get("ordered_cards") or dashboard_data.get("dashcards") or []

    prepared: list[dict[str, Any]] = []
    for idx, dc in enumerate(raw_dashcards, start=1):
        cleaned: dict[str, Any] = {"id": -idx}
        for key in _DASHCARD_ALLOWED_FIELDS:
            if key in dc:
                cleaned[key] = dc[key]

        # Apply card ID mapping if provided
        if card_id_mapping and cleaned.get("card_id") in card_id_mapping:
            cleaned["card_id"] = card_id_mapping[cleaned["card_id"]]

        prepared.append(cleaned)

    return prepared


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
    """List dashboards. Requires --collection-id to avoid slow unfiltered queries."""
    if collection_id is None:
        msg = (
            "--collection-id is required."
            " Use 'metabase search <query> --models dashboard' to search without a collection filter."
        )
        if json_output:
            output_error_json(code="VALIDATION_ERROR", message=msg)
        else:
            error_console.print(f"[red]{msg}[/red]")
        raise typer.Exit(1)

    ctx = get_context()

    try:
        client = ctx.require_auth()
        dashboards = client.dashboards.list(collection_id=collection_id)

        if json_output:
            # Build output data
            dashboard_list = []
            for dashboard in dashboards:
                dashboard_entry = {
                    "id": dashboard.get("id"),
                    "name": dashboard.get("name"),
                    "collection_id": dashboard.get("collection_id"),
                    "archived": dashboard.get("archived", False),
                }
                # Include collection name if available
                collection = dashboard.get("collection")
                if collection and isinstance(collection, dict):
                    dashboard_entry["collection_name"] = collection.get("name")

                dashboard_list.append(dashboard_entry)

            output_json({"dashboards": dashboard_list})
        else:
            # Human-readable bullet list output
            if not dashboards:
                console.print("[dim]No dashboards found.[/dim]")
            else:
                console.print(f"[bold]Dashboards ({len(dashboards)}):[/bold]")
                for dashboard in dashboards:
                    name = dashboard.get("name", "Unknown")
                    dash_id = dashboard.get("id", "")

                    collection = dashboard.get("collection")
                    collection_name = ""
                    if collection and isinstance(collection, dict):
                        collection_name = collection.get("name", "")
                    elif dashboard.get("collection_id"):
                        collection_name = f"(ID: {dashboard.get('collection_id')})"

                    parts = [f"id: {dash_id}"]
                    if collection_name:
                        parts.append(f"collection: {collection_name}")

                    console.print(f"* {name} ({', '.join(parts)})")

    except Exception as e:
        handle_api_error(e, json_output, "Dashboard")
        raise typer.Exit(1) from None


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
    ctx = get_context()

    try:
        client = ctx.require_auth()
        dashboard_data = client.dashboards.get(dashboard_id)
        dashboard = Dashboard.from_dict(dashboard_data)

        # Fetch referenced cards if requested
        referenced_cards: dict[int, dict[str, Any]] = {}
        if include_cards:
            card_ids = dashboard.get_unique_card_ids()
            for card_id in card_ids:
                try:
                    card_data = client.cards.get(card_id)
                    referenced_cards[card_id] = card_data
                except NotFoundError:
                    # Card might have been deleted, skip it
                    pass

        if json_output:
            # Build output data
            output_data: dict[str, Any] = {
                "id": dashboard.id,
                "name": dashboard.name,
                "description": dashboard.description,
                "collection_id": dashboard.collection_id,
                "parameters": dashboard.parameters,
                "tabs": dashboard.tabs,
                "archived": dashboard.archived,
            }

            # Include collection info if available
            if dashboard.collection_name:
                _, path_parts = get_collection_path_parts(dashboard_data)
                output_data["collection"] = {
                    "id": dashboard.collection_id,
                    "name": dashboard.collection_name,
                    "path": path_parts,
                }

            # Include dashcards
            output_data["dashcards"] = []
            for dc in dashboard.dashcards:
                dc_data = {
                    "id": dc.id,
                    "card_id": dc.card_id,
                    "row": dc.row,
                    "col": dc.col,
                    "size_x": dc.size_x,
                    "size_y": dc.size_y,
                    "parameter_mappings": dc.parameter_mappings,
                    "visualization_settings": dc.visualization_settings,
                }
                output_data["dashcards"].append(dc_data)

            # Include referenced cards if fetched
            if referenced_cards:
                output_data["referenced_cards"] = referenced_cards

            if dashboard.created_at:
                output_data["created_at"] = dashboard.created_at.isoformat()
            if dashboard.updated_at:
                output_data["updated_at"] = dashboard.updated_at.isoformat()

            output_json(output_data)
        else:
            # Human-readable output
            console.print(f"[bold]Dashboard:[/bold] {dashboard.name}")
            console.print(f"[dim]ID:[/dim] {dashboard.id}")

            if dashboard.description:
                console.print(f"[dim]Description:[/dim] {dashboard.description}")

            # Collection info
            if dashboard.collection_name:
                console.print(f"[dim]Collection:[/dim] {dashboard.collection_name} (ID: {dashboard.collection_id})")
            elif dashboard.collection_id:
                console.print(f"[dim]Collection ID:[/dim] {dashboard.collection_id}")

            # Tabs info
            if dashboard.tabs:
                console.print(f"[dim]Tabs:[/dim] {len(dashboard.tabs)}")

            # Cards summary
            card_ids = dashboard.get_unique_card_ids()
            console.print(f"[dim]Cards:[/dim] {len(card_ids)} unique cards")

            if dashboard.dashcards:
                console.print(f"[dim]Dashcards:[/dim] {len(dashboard.dashcards)} placements")

            if dashboard.parameters:
                console.print(f"[dim]Parameters:[/dim] {len(dashboard.parameters)}")

            if dashboard.archived:
                console.print("\n[yellow]This dashboard is archived[/yellow]")

            # Show card details if requested
            if include_cards and referenced_cards:
                console.print("\n[bold]Referenced Cards:[/bold]")
                for card_id, card_data in referenced_cards.items():
                    console.print(f"  - {card_data.get('name', 'Unknown')} (ID: {card_id})")

    except Exception as e:
        handle_api_error(e, json_output, "Dashboard")
        raise typer.Exit(1) from None


@app.command("export")
def export_dashboard(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Return file paths as JSON."),
    ] = False,
) -> None:
    """Export a complete dashboard with all referenced cards."""
    ctx = get_context()

    try:
        client = ctx.require_auth()

        if not json_output:
            console.print(f"Exporting dashboard {dashboard_id}...")
            console.print()
            console.print("Fetching dashboard details... ", end="")

        # Fetch dashboard
        dashboard_data = client.dashboards.get(dashboard_id)
        dashboard = Dashboard.from_dict(dashboard_data)

        if not json_output:
            console.print("[green]done[/green]")

        # Get unique card IDs
        card_ids = dashboard.get_unique_card_ids()

        if not json_output:
            console.print(f"Found {len(card_ids)} referenced cards")

        # Fetch all referenced cards
        cards: dict[int, dict[str, Any]] = {}
        for card_id in card_ids:
            try:
                if not json_output:
                    console.print(f"Exporting card {card_id}... ", end="")
                card_data = client.cards.get(card_id)
                cards[card_id] = card_data
                if not json_output:
                    console.print(f"[green]done[/green] ({card_data.get('name', 'Unknown')})")
            except NotFoundError:
                if not json_output:
                    console.print("[yellow]not found (skipped)[/yellow]")

        # Create export directory
        export_dir = create_export_dir()

        # Get source info
        config = ctx.config
        source_info = {
            "instance_url": config.url if config else "",
            "dashboard_id": dashboard_id,
        }

        # Strip embedded card objects from dashcards before exporting.
        # Cards are exported as separate files, so the full card definition
        # inside each dashcard is redundant and confusing for agents editing
        # the JSON. We keep only the layout/placement fields.
        dashcards_key = "ordered_cards" if "ordered_cards" in dashboard_data else "dashcards"
        raw_dashcards = dashboard_data.get(dashcards_key, [])
        cleaned_dashcards = []
        for dc in raw_dashcards:
            cleaned: dict[str, Any] = {"id": dc.get("id")}
            for key in _DASHCARD_ALLOWED_FIELDS:
                if key in dc:
                    cleaned[key] = dc[key]
            cleaned_dashcards.append(cleaned)
        export_data = {**dashboard_data}
        export_data.pop("ordered_cards", None)
        export_data["dashcards"] = cleaned_dashcards

        # Write dashboard file
        dashboard_filename = f"dashboard-{dashboard_id}.json"
        write_export_file(
            export_dir,
            dashboard_filename,
            export_data,
            "dashboard",
            source_info,
        )

        # Write card files
        card_files: list[dict[str, Any]] = []
        for card_id, card_data in cards.items():
            card_filename = f"card-{card_id}.json"
            card_source_info = {
                "instance_url": config.url if config else "",
                "card_id": card_id,
                "database_id": card_data.get("database_id"),
            }
            write_export_file(
                export_dir,
                card_filename,
                card_data,
                "card",
                card_source_info,
            )
            card_files.append(
                {
                    "id": card_id,
                    "name": card_data.get("name", ""),
                    "file": card_filename,
                }
            )

        # Write manifest
        manifest = {
            "export_version": EXPORT_VERSION,
            "export_timestamp": datetime.now().isoformat() + "Z",
            "source": {
                "instance_url": config.url if config else "",
            },
            "dashboard": {
                "id": dashboard_id,
                "name": dashboard.name,
                "file": dashboard_filename,
            },
            "cards": card_files,
        }
        manifest_path = write_json_file(export_dir, "manifest.json", manifest)

        if json_output:
            output_json(
                {
                    "output_dir": str(export_dir),
                    "manifest": str(manifest_path),
                    "dashboard": {
                        "id": dashboard_id,
                        "name": dashboard.name,
                        "file": str(export_dir / dashboard_filename),
                    },
                    "cards": [
                        {
                            "id": cf["id"],
                            "name": cf["name"],
                            "file": str(export_dir / cf["file"]),
                        }
                        for cf in card_files
                    ],
                }
            )
        else:
            console.print()
            console.print("[bold green]Export complete![/bold green]")
            console.print(f"Output directory: {export_dir}")
            console.print()
            console.print("[bold]Files created:[/bold]")
            console.print("  - manifest.json")
            console.print(f"  - {dashboard_filename}")
            for cf in card_files:
                console.print(f"  - {cf['file']} ({cf['name']})")

    except Exception as e:
        handle_api_error(e, json_output, "Dashboard")
        raise typer.Exit(1) from None


@app.command("import")
def import_dashboard(
    file: Annotated[
        str | None,
        typer.Option("--file", help="Path to dashboard JSON file (or use stdin with '-')."),
    ] = None,
    dashboard_id: Annotated[
        int | None,
        typer.Option("--id", help="Dashboard ID to update (if omitted, creates new)."),
    ] = None,
    collection_id: Annotated[
        int | None,
        typer.Option("--collection-id", help="Target collection."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Import a dashboard from a JSON definition file.

    Creates or updates a dashboard layout. Cards must already exist — use
    'metabase cards import' to create them first. Dashcards reference
    existing cards by card_id.
    """
    ctx = get_context()

    try:
        # Read input from file or stdin
        if file == "-" or file is None:
            if sys.stdin.isatty():
                output_error_json(
                    code="VALIDATION_ERROR",
                    message="No input provided. Use --file or pipe JSON to stdin.",
                )
                raise typer.Exit(1)
            input_json = sys.stdin.read()
        else:
            try:
                input_json = Path(file).read_text()
            except FileNotFoundError:
                output_error_json(
                    code="FILE_ERROR",
                    message=f"File not found: {file}",
                )
                raise typer.Exit(1) from None
            except OSError as e:
                output_error_json(
                    code="FILE_ERROR",
                    message=f"Error reading file: {e}",
                )
                raise typer.Exit(1) from None

        # Parse JSON
        try:
            input_data = json.loads(input_json)
        except json.JSONDecodeError as e:
            output_error_json(
                code="VALIDATION_ERROR",
                message=f"Invalid JSON: {e}",
            )
            raise typer.Exit(1) from None

        # Unwrap export envelope if present
        if "export_version" in input_data and "type" in input_data and input_data.get("type") == "dashboard":
            dashboard_data = input_data.get("dashboard", input_data)
        else:
            dashboard_data = input_data

        # Apply overrides
        if collection_id is not None:
            dashboard_data["collection_id"] = collection_id

        # Remove read-only fields
        for field_name in _DASHBOARD_READONLY_FIELDS:
            dashboard_data.pop(field_name, None)

        # Prepare dashcards: clean fields, assign negative IDs
        prepared_dashcards = _prepare_dashcards_for_import(dashboard_data)
        dashboard_data["dashcards"] = prepared_dashcards
        dashboard_data.pop("ordered_cards", None)

        client = ctx.require_auth()

        if dashboard_id is not None:
            # Update existing dashboard
            result_data = client.dashboards.update(dashboard_id, dashboard_data)
            output_json(
                {
                    "dashboard": {
                        "id": result_data.get("id"),
                        "name": result_data.get("name"),
                        "action": "updated",
                    }
                }
            )
        else:
            # Create new dashboard in two steps:
            # 1. POST to create the shell (Metabase ignores dashcards on POST)
            # 2. PUT to attach the dashcards
            dashcards = dashboard_data.pop("dashcards", [])
            result_data = client.dashboards.create(dashboard_data)
            new_dashboard_id = result_data.get("id")

            if dashcards and new_dashboard_id:
                client.dashboards.update(new_dashboard_id, {"dashcards": dashcards})

            output_json(
                {
                    "dashboard": {
                        "id": new_dashboard_id,
                        "name": result_data.get("name"),
                        "action": "created",
                    }
                }
            )

    except typer.Exit:
        raise
    except Exception as e:
        handle_api_error(e, json_output=True, entity_name="Dashboard")
        raise typer.Exit(1) from None


@app.command("archive")
def archive_dashboard(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Archive a dashboard (soft delete)."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        result = client.dashboards.archive(dashboard_id)

        if json_output:
            output_json(
                {
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "archived": True,
                }
            )
        else:
            console.print(f"[green]Dashboard {dashboard_id} archived successfully.[/green]")

    except Exception as e:
        handle_api_error(e, json_output, "Dashboard")
        raise typer.Exit(1) from None


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
    ctx = get_context()

    try:
        client = ctx.require_auth()

        # Get dashboard info first for confirmation
        dashboard_info = client.dashboards.get(dashboard_id)
        dashboard_name = dashboard_info.get("name", f"Dashboard {dashboard_id}")

        if not force and not json_output:
            # Prompt for confirmation
            confirm = typer.confirm(
                f"Are you sure you want to permanently delete dashboard '{dashboard_name}' (ID: {dashboard_id})?"
            )
            if not confirm:
                console.print("[yellow]Deletion cancelled.[/yellow]")
                raise typer.Exit(0)

        client.dashboards.delete(dashboard_id)

        if json_output:
            output_json(
                {
                    "id": dashboard_id,
                    "name": dashboard_name,
                    "deleted": True,
                }
            )
        else:
            console.print(f"[green]Dashboard {dashboard_id} deleted successfully.[/green]")

    except typer.Exit:
        raise
    except Exception as e:
        handle_api_error(e, json_output, "Dashboard")
        raise typer.Exit(1) from None


@app.command("revisions")
def list_revisions(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List dashboard revisions."""
    ctx = get_context()

    try:
        client = ctx.require_auth()

        # Get dashboard info for context
        dashboard_info = client.dashboards.get(dashboard_id)
        dashboard_name = dashboard_info.get("name", f"Dashboard {dashboard_id}")

        # Get revisions
        revisions = client.dashboards.list_revisions(dashboard_id)

        if json_output:
            output_json(
                {
                    "dashboard_id": dashboard_id,
                    "dashboard_name": dashboard_name,
                    "revisions": revisions,
                }
            )
        else:
            console.print(f"[bold]Revisions for Dashboard:[/bold] {dashboard_name} (ID: {dashboard_id})")
            console.print()

            if not revisions:
                console.print("[dim]No revisions found.[/dim]")
            else:
                console.print(f"[bold]Revisions ({len(revisions)}):[/bold]")
                for rev in revisions:
                    rev_id = rev.get("id", "")
                    user = rev.get("user", {})
                    user_name = ""
                    if isinstance(user, dict):
                        user_name = user.get("common_name") or user.get("email", "")
                    timestamp = rev.get("timestamp", "")
                    description = (rev.get("description") or "").strip()

                    parts = [f"id: {rev_id}"]
                    if user_name:
                        parts.append(f"user: {user_name}")
                    if timestamp:
                        parts.append(f"at: {timestamp}")

                    line = f"* Revision ({', '.join(parts)})"
                    if description:
                        line += f" - {description}"
                    console.print(line)

    except Exception as e:
        handle_api_error(e, json_output, "Dashboard")
        raise typer.Exit(1) from None


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
    ctx = get_context()

    try:
        client = ctx.require_auth()
        result = client.dashboards.revert(dashboard_id, revision_id)

        if json_output:
            output_json(
                {
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "reverted_to": revision_id,
                }
            )
        else:
            dashboard_name = result.get("name", f"Dashboard {dashboard_id}")
            console.print(
                f"[green]Dashboard '{dashboard_name}' reverted to revision {revision_id} successfully.[/green]"
            )

    except Exception as e:
        handle_api_error(e, json_output, "Dashboard")
        raise typer.Exit(1) from None
