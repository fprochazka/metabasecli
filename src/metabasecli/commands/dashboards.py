"""Dashboard commands."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table

from ..client.base import NotFoundError
from ..constants import EXPORT_VERSION
from ..context import get_context
from ..logging import console
from ..models.dashboard import Dashboard
from ..output import (
    create_export_dir,
    handle_api_error,
    output_error_json,
    output_json,
    write_export_file,
    write_json_file,
)

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
            # Human-readable table output
            table = Table(title="Dashboards")
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Name", style="green")
            table.add_column("Collection", style="magenta")

            for dashboard in dashboards:
                collection = dashboard.get("collection")
                collection_name = ""
                if collection and isinstance(collection, dict):
                    collection_name = collection.get("name", "")
                elif dashboard.get("collection_id"):
                    collection_name = f"(ID: {dashboard.get('collection_id')})"

                table.add_row(
                    str(dashboard.get("id", "")),
                    dashboard.get("name", ""),
                    collection_name,
                )

            console.print(table)

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
                output_data["collection"] = {
                    "id": dashboard.collection_id,
                    "name": dashboard.collection_name,
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

        # Write dashboard file
        dashboard_filename = f"dashboard-{dashboard_id}.json"
        write_export_file(
            export_dir,
            dashboard_filename,
            dashboard_data,
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
    ctx = get_context()

    try:
        # Read input from file or stdin
        if file == "-" or file is None:
            # Read from stdin
            if sys.stdin.isatty():
                output_error_json(
                    code="VALIDATION_ERROR",
                    message="No input provided. Use --file or pipe JSON to stdin.",
                )
                raise typer.Exit(1)
            input_json = sys.stdin.read()
            file_path = None
        else:
            # Read from file
            try:
                file_path = Path(file)
                input_json = file_path.read_text()
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

        # Determine if this is a manifest or a direct dashboard file
        is_manifest = "dashboard" in input_data and "cards" in input_data and "export_version" in input_data
        is_export_file = "export_version" in input_data and "type" in input_data

        dashboard_data: dict[str, Any]
        card_files_to_import: list[Path] = []

        if is_manifest:
            # This is a manifest.json file
            if file_path is None:
                output_error_json(
                    code="VALIDATION_ERROR",
                    message="Manifest import requires a file path (cannot use stdin).",
                )
                raise typer.Exit(1) from None

            manifest_dir = file_path.parent

            # Read dashboard file
            dashboard_file = manifest_dir / input_data["dashboard"]["file"]
            try:
                dashboard_export = json.loads(dashboard_file.read_text())
                dashboard_data = dashboard_export.get("dashboard", dashboard_export)
            except FileNotFoundError:
                output_error_json(
                    code="FILE_ERROR",
                    message=f"Dashboard file not found: {dashboard_file}",
                )
                raise typer.Exit(1) from None

            # Get card file paths
            for card_entry in input_data.get("cards", []):
                card_files_to_import.append(manifest_dir / card_entry["file"])

        elif is_export_file and input_data.get("type") == "dashboard":
            # This is a dashboard export file
            dashboard_data = input_data.get("dashboard", input_data)
        else:
            # Assume it's a raw dashboard definition
            dashboard_data = input_data

        # Apply overrides
        if collection_id is not None:
            dashboard_data["collection_id"] = collection_id

        # Remove fields that shouldn't be sent on create/update
        fields_to_remove = [
            "id",
            "creator_id",
            "created_at",
            "updated_at",
            "made_public_by_id",
            "public_uuid",
            "entity_id",
            "collection",
            "creator",
            "embedding_params",
        ]
        for field_name in fields_to_remove:
            dashboard_data.pop(field_name, None)

        # Handle dry run
        if dry_run:
            result: dict[str, Any] = {
                "dry_run": True,
                "dashboard": {
                    "name": dashboard_data.get("name"),
                    "action": "update" if dashboard_id else "create",
                },
                "cards": [],
            }
            for card_file in card_files_to_import:
                try:
                    card_export = json.loads(card_file.read_text())
                    card_data = card_export.get("card", card_export)
                    result["cards"].append(
                        {
                            "name": card_data.get("name"),
                            "action": "create",
                        }
                    )
                except (FileNotFoundError, json.JSONDecodeError):
                    pass
            output_json(result)
            return

        client = ctx.require_auth()
        imported_cards: list[dict[str, Any]] = []

        # Import cards first (if not dashboard_only)
        if not dashboard_only and card_files_to_import:
            for card_file in card_files_to_import:
                try:
                    card_export = json.loads(card_file.read_text())
                    card_data = card_export.get("card", card_export)

                    # Apply overrides
                    if collection_id is not None:
                        card_data["collection_id"] = collection_id
                    if database_id is not None:
                        if "dataset_query" in card_data:
                            card_data["dataset_query"]["database"] = database_id
                        card_data["database_id"] = database_id

                    # Remove fields that shouldn't be sent
                    card_fields_to_remove = [
                        "id",
                        "creator",
                        "created_at",
                        "updated_at",
                        "made_public_by_id",
                        "public_uuid",
                        "entity_id",
                        "collection",
                        "creator_id",
                    ]
                    for field_name in card_fields_to_remove:
                        card_data.pop(field_name, None)

                    # Create card
                    created_card = client.cards.create(card_data)
                    imported_cards.append(
                        {
                            "id": created_card.get("id"),
                            "name": created_card.get("name"),
                            "action": "created",
                        }
                    )
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    imported_cards.append(
                        {
                            "file": str(card_file),
                            "action": "failed",
                            "error": str(e),
                        }
                    )

        # Import dashboard (if not cards_only)
        dashboard_result: dict[str, Any] | None = None
        if not cards_only:
            if dashboard_id is not None:
                # Update existing dashboard
                result_data = client.dashboards.update(dashboard_id, dashboard_data)
                dashboard_result = {
                    "id": result_data.get("id"),
                    "name": result_data.get("name"),
                    "action": "updated",
                }
            else:
                # Create new dashboard
                result_data = client.dashboards.create(dashboard_data)
                dashboard_result = {
                    "id": result_data.get("id"),
                    "name": result_data.get("name"),
                    "action": "created",
                }

        # Output result (JSON only as per spec)
        output_result: dict[str, Any] = {}
        if dashboard_result:
            output_result["dashboard"] = dashboard_result
        if imported_cards:
            output_result["cards"] = imported_cards

        output_json(output_result)

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
                table = Table()
                table.add_column("Revision ID", style="cyan", justify="right")
                table.add_column("User", style="green")
                table.add_column("Description", style="white")
                table.add_column("Timestamp", style="dim")

                for rev in revisions:
                    user = rev.get("user", {})
                    user_name = ""
                    if isinstance(user, dict):
                        user_name = user.get("common_name") or user.get("email", "")

                    table.add_row(
                        str(rev.get("id", "")),
                        user_name,
                        rev.get("description", ""),
                        rev.get("timestamp", ""),
                    )

                console.print(table)

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
