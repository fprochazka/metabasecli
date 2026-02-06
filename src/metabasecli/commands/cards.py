"""Card (saved question) commands.

Provides commands for managing Metabase cards including listing, viewing,
running queries, importing, and archiving/deleting cards.
"""

import json
import sys
from typing import Annotated, Any

import typer
from rich.table import Table

from ..context import get_context
from ..logging import console, error_console
from ..output import (
    create_export_dir,
    get_collection_path_parts,
    handle_api_error,
    output_error_json,
    output_json,
    write_csv_file,
    write_json_file,
)

app = typer.Typer(name="cards", help="Card/query operations.")


def _convert_query_result_to_csv(
    result: dict[str, Any],
) -> tuple[list[str], list[list[Any]]]:
    """Convert Metabase query result to CSV format.

    Args:
        result: Query result from Metabase API containing 'data' with 'cols' and 'rows'.

    Returns:
        Tuple of (headers, rows) ready for CSV writing.
    """
    data = result.get("data", {})
    cols = data.get("cols", [])
    rows = data.get("rows", [])

    # Extract column headers
    headers = []
    for col in cols:
        # Prefer display_name, fall back to name
        name = col.get("display_name") or col.get("name") or "column"
        headers.append(str(name))

    # Convert row values to strings, handling nested data
    csv_rows = []
    for row in rows:
        csv_row = []
        for value in row:
            if value is None:
                csv_row.append("")
            elif isinstance(value, (dict, list)):
                # Serialize complex types as JSON
                csv_row.append(json.dumps(value, default=str))
            else:
                csv_row.append(value)
        csv_rows.append(csv_row)

    return headers, csv_rows


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
    ctx = get_context()

    try:
        client = ctx.require_auth()
        cards = client.cards.list(
            filter_type=filter_type,
            collection_id=collection_id,
            database_id=database_id,
        )

        if json_output:
            # Build output data
            card_list = []
            for card in cards:
                card_entry = {
                    "id": card.get("id"),
                    "name": card.get("name"),
                    "display": card.get("display"),
                    "collection_id": card.get("collection_id"),
                    "database_id": card.get("database_id"),
                    "archived": card.get("archived", False),
                }
                # Include collection name if available
                collection = card.get("collection")
                if collection and isinstance(collection, dict):
                    card_entry["collection_name"] = collection.get("name")

                card_list.append(card_entry)

            output_json({"cards": card_list})
        else:
            # Human-readable table output
            table = Table(title="Cards")
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Name", style="green")
            table.add_column("Display", style="blue")
            table.add_column("Collection", style="magenta")

            for card in cards:
                collection = card.get("collection")
                collection_name = ""
                if collection and isinstance(collection, dict):
                    collection_name = collection.get("name", "")
                elif card.get("collection_id"):
                    collection_name = f"(ID: {card.get('collection_id')})"

                table.add_row(
                    str(card.get("id", "")),
                    card.get("name", ""),
                    card.get("display", ""),
                    collection_name,
                )

            console.print(table)

    except Exception as e:
        handle_api_error(e, json_output, "Card")
        raise typer.Exit(1) from None


@app.command("get")
def get_card(
    card_id: Annotated[int, typer.Argument(help="Card ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Get card details including full query definition."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        card = client.cards.get(card_id)

        if json_output:
            # Build curated output with collection path
            collection = card.get("collection")
            collection_data = None
            if collection and isinstance(collection, dict):
                _, path_parts = get_collection_path_parts(card)
                collection_data = {
                    "id": collection.get("id"),
                    "name": collection.get("name"),
                    "path": path_parts,
                }

            curated: dict[str, Any] = {
                "id": card.get("id"),
                "name": card.get("name"),
                "description": card.get("description"),
                "collection_id": card.get("collection_id"),
                "collection": collection_data,
                "database_id": card.get("database_id"),
                "dataset_query": card.get("dataset_query"),
                "display": card.get("display"),
                "visualization_settings": card.get("visualization_settings"),
                "parameters": card.get("parameters"),
                "created_at": card.get("created_at"),
                "updated_at": card.get("updated_at"),
            }
            output_json(curated)
        else:
            # Human-readable output
            console.print(f"[bold]Card:[/bold] {card.get('name', 'Unknown')}")
            console.print(f"[dim]ID:[/dim] {card.get('id', 'N/A')}")
            console.print(f"[dim]Display:[/dim] {card.get('display', 'N/A')}")

            if card.get("description"):
                console.print(f"[dim]Description:[/dim] {card.get('description')}")

            # Collection info
            collection = card.get("collection")
            if collection and isinstance(collection, dict):
                coll_name = collection.get("name", "N/A")
                coll_id = card.get("collection_id")
                console.print(f"[dim]Collection:[/dim] {coll_name} (ID: {coll_id})")
            elif card.get("collection_id"):
                console.print(f"[dim]Collection ID:[/dim] {card.get('collection_id')}")

            # Database info
            console.print(f"[dim]Database ID:[/dim] {card.get('database_id', 'N/A')}")

            # Query info
            dataset_query = card.get("dataset_query", {})
            query_type = dataset_query.get("type", "unknown")
            console.print(f"[dim]Query Type:[/dim] {query_type}")

            if query_type == "native":
                native = dataset_query.get("native", {})
                query = native.get("query", "")
                if query:
                    console.print("\n[bold]Query:[/bold]")
                    console.print(query)
            elif query_type == "query":
                mbql = dataset_query.get("query", {})
                if mbql:
                    console.print("\n[bold]MBQL Query:[/bold]")
                    console.print(json.dumps(mbql, indent=2))

            if card.get("archived"):
                console.print("\n[yellow]This card is archived[/yellow]")

    except Exception as e:
        handle_api_error(e, json_output, "Card")
        raise typer.Exit(1) from None


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
    ctx = get_context()

    try:
        client = ctx.require_auth()

        # First, get the card info for the name
        card_info = client.cards.get(card_id)
        card_name = card_info.get("name", f"Card {card_id}")

        # Parse parameters if provided
        params_dict = None
        if parameters:
            try:
                params_dict = json.loads(parameters)
            except json.JSONDecodeError as e:
                if json_output:
                    output_error_json(
                        code="VALIDATION_ERROR",
                        message=f"Invalid JSON in parameters: {e}",
                    )
                else:
                    error_console.print(f"[red]Invalid JSON in parameters: {e}[/red]")
                raise typer.Exit(1) from None

        # Execute the query
        result = client.cards.run(card_id, parameters=params_dict, limit=limit)

        # Create export directory
        export_dir = create_export_dir()

        # Get row count
        data = result.get("data", {})
        row_count = len(data.get("rows", []))

        # Write JSON file
        json_filename = f"card-{card_id}-results.json"
        json_path = write_json_file(export_dir, json_filename, result)

        # Convert to CSV and write
        headers, rows = _convert_query_result_to_csv(result)
        csv_filename = f"card-{card_id}-results.csv"
        csv_path = write_csv_file(export_dir, csv_filename, headers, rows)

        if json_output:
            output_json(
                {
                    "card_id": card_id,
                    "card_name": card_name,
                    "row_count": row_count,
                    "files": {
                        "json": str(json_path),
                        "csv": str(csv_path),
                    },
                }
            )
        else:
            console.print(f"Executing card {card_id}: {card_name}")
            console.print(f"Rows returned: {row_count}")
            console.print()
            console.print("[bold]Output files:[/bold]")
            console.print(f"  - {json_path}")
            console.print(f"  - {csv_path}")

    except Exception as e:
        handle_api_error(e, json_output, "Card")
        raise typer.Exit(1) from None


@app.command("import")
def import_card(
    file: Annotated[
        str | None,
        typer.Option("--file", help="Path to card JSON file (or use stdin with '-')."),
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
    ctx = get_context()

    try:
        # Read card data from file or stdin
        if file == "-" or file is None:
            # Read from stdin
            if sys.stdin.isatty():
                # No piped input and no file specified
                output_error_json(
                    code="VALIDATION_ERROR",
                    message="No input provided. Use --file or pipe JSON to stdin.",
                )
                raise typer.Exit(1)
            card_json = sys.stdin.read()
        else:
            # Read from file
            try:
                with open(file) as f:
                    card_json = f.read()
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
            card_data = json.loads(card_json)
        except json.JSONDecodeError as e:
            output_error_json(
                code="VALIDATION_ERROR",
                message=f"Invalid JSON: {e}",
            )
            raise typer.Exit(1) from None

        # Handle export file format - extract the card data if wrapped
        if "export_version" in card_data and "card" in card_data:
            card_data = card_data["card"]

        # Validate required fields for create
        if card_id is None:
            # Creating new card - need required fields
            if "name" not in card_data:
                output_error_json(
                    code="VALIDATION_ERROR",
                    message="Card JSON must contain 'name' field.",
                )
                raise typer.Exit(1) from None
            if "dataset_query" not in card_data:
                output_error_json(
                    code="VALIDATION_ERROR",
                    message="Card JSON must contain 'dataset_query' field.",
                )
                raise typer.Exit(1) from None

        # Apply overrides
        if collection_id is not None:
            card_data["collection_id"] = collection_id
        if database_id is not None:
            # Update database in dataset_query
            if "dataset_query" in card_data:
                card_data["dataset_query"]["database"] = database_id
            card_data["database_id"] = database_id

        # Remove fields that shouldn't be sent on create/update
        fields_to_remove = ["id", "creator", "created_at", "updated_at", "made_public_by_id", "public_uuid"]
        for field_name in fields_to_remove:
            card_data.pop(field_name, None)

        client = ctx.require_auth()

        if card_id is not None:
            # Update existing card
            result = client.cards.update(card_id, card_data)
            action = "updated"
        else:
            # Create new card
            result = client.cards.create(card_data)
            action = "created"

        # Output result (JSON only as per spec)
        output_json(
            {
                "id": result.get("id"),
                "name": result.get("name"),
                "action": action,
            }
        )

    except typer.Exit:
        raise
    except Exception as e:
        handle_api_error(e, json_output=True, entity_name="Card")
        raise typer.Exit(1) from None


@app.command("archive")
def archive_card(
    card_id: Annotated[int, typer.Argument(help="Card ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Archive a card (soft delete)."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        result = client.cards.archive(card_id)

        if json_output:
            output_json(
                {
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "archived": True,
                }
            )
        else:
            console.print(f"[green]Card {card_id} archived successfully.[/green]")

    except Exception as e:
        handle_api_error(e, json_output, "Card")
        raise typer.Exit(1) from None


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
    ctx = get_context()

    try:
        client = ctx.require_auth()

        # Get card info first for confirmation
        card_info = client.cards.get(card_id)
        card_name = card_info.get("name", f"Card {card_id}")

        if not force and not json_output:
            # Prompt for confirmation
            confirm = typer.confirm(f"Are you sure you want to permanently delete card '{card_name}' (ID: {card_id})?")
            if not confirm:
                console.print("[yellow]Deletion cancelled.[/yellow]")
                raise typer.Exit(0)

        client.cards.delete(card_id)

        if json_output:
            output_json(
                {
                    "id": card_id,
                    "name": card_name,
                    "deleted": True,
                }
            )
        else:
            console.print(f"[green]Card {card_id} deleted successfully.[/green]")

    except typer.Exit:
        raise
    except Exception as e:
        handle_api_error(e, json_output, "Card")
        raise typer.Exit(1) from None
