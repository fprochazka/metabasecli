"""Search command."""

from collections import defaultdict
from typing import Annotated

import typer
from rich.table import Table

from ..client.base import MetabaseAPIError, NotFoundError
from ..context import get_context
from ..logging import console, error_console
from ..output import output_error_json, output_json


def _handle_error(e: Exception, json_output: bool) -> None:
    """Handle API errors consistently."""
    if isinstance(e, NotFoundError):
        if json_output:
            output_error_json(
                code="NOT_FOUND",
                message=str(e),
                details={"status_code": e.status_code} if e.status_code else None,
            )
        else:
            error_console.print(f"[red]Not found: {e}[/red]")
    elif isinstance(e, MetabaseAPIError):
        if json_output:
            output_error_json(
                code="API_ERROR",
                message=str(e),
                details={"status_code": e.status_code} if e.status_code else None,
            )
        else:
            error_console.print(f"[red]API error: {e}[/red]")
    else:
        if json_output:
            output_error_json(code="ERROR", message=str(e))
        else:
            error_console.print(f"[red]Error: {e}[/red]")


def _get_collection_path(item: dict) -> str:
    """Get the collection path for an item."""
    collection = item.get("collection") or {}
    if not collection:
        return "Root Collection"

    # Try to build path from effective_ancestors if available
    ancestors = collection.get("effective_ancestors", [])
    if ancestors:
        path_parts = [a.get("name", "") for a in ancestors if a.get("name")]
        path_parts.append(collection.get("name", ""))
        return " / ".join(path_parts)

    # Fallback to just collection name
    return collection.get("name", "Root Collection")


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
    ctx = get_context()

    try:
        client = ctx.require_auth()

        # Parse models if provided
        model_list: list[str] | None = None
        if models:
            model_list = [m.strip() for m in models.split(",") if m.strip()]

        # Perform search
        results = client.search.search(
            query=query,
            models=model_list,
            collection_id=collection_id,
            database_id=database_id,
            archived=archived,
            created_by=created_by,
            limit=limit,
        )

        data = results.get("data", [])
        total = results.get("total", len(data))

        if json_output:
            # Build JSON output
            formatted_results = []
            for item in data:
                result_entry = {
                    "id": item.get("id"),
                    "model": item.get("model"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                }

                # Add collection info if available
                collection = item.get("collection")
                if collection:
                    ancestors = collection.get("effective_ancestors", [])
                    path = [a.get("name", "") for a in ancestors if a.get("name")]
                    path.append(collection.get("name", ""))
                    result_entry["collection"] = {
                        "id": collection.get("id"),
                        "name": collection.get("name"),
                        "path": path,
                    }

                # Add updated_at if available
                if item.get("updated_at"):
                    result_entry["updated_at"] = item.get("updated_at")

                formatted_results.append(result_entry)

            output_json(
                {
                    "query": query,
                    "total_results": total,
                    "results": formatted_results,
                }
            )
        else:
            # Human-readable output grouped by model type
            if not data:
                console.print(f"[dim]No results found for '[/dim]{query}[dim]'[/dim]")
                return

            # Group results by model type
            grouped: dict[str, list] = defaultdict(list)
            for item in data:
                model_type = item.get("model", "unknown")
                grouped[model_type].append(item)

            # Print summary
            console.print(f"\n[bold]Search results for '[/bold]{query}[bold]'[/bold]")
            console.print(f"[dim]Found {total} results[/dim]\n")

            # Print counts by type
            type_counts = []
            for model_type, items in sorted(grouped.items()):
                type_counts.append(f"{model_type}: {len(items)}")
            console.print(f"[dim]By type: {', '.join(type_counts)}[/dim]\n")

            # Define display order for model types
            model_order = [
                "dashboard",
                "card",
                "collection",
                "table",
                "database",
                "dataset",
                "metric",
                "segment",
                "action",
            ]

            # Print each group
            for model_type in model_order:
                if model_type not in grouped:
                    continue

                items = grouped[model_type]
                console.print(f"[bold cyan]{model_type.upper()}S ({len(items)})[/bold cyan]")

                table = Table(show_header=True, header_style="bold")
                table.add_column("ID", style="cyan", justify="right", width=8)
                table.add_column("Name", style="green", min_width=20)
                table.add_column("Location", style="dim", min_width=30)

                for item in items:
                    item_id = str(item.get("id", ""))
                    name = item.get("name", "")
                    location = _get_collection_path(item)

                    table.add_row(item_id, name, location)

                console.print(table)
                console.print()

            # Print any remaining types not in the predefined order
            remaining = set(grouped.keys()) - set(model_order)
            for model_type in sorted(remaining):
                items = grouped[model_type]
                console.print(f"[bold cyan]{model_type.upper()}S ({len(items)})[/bold cyan]")

                table = Table(show_header=True, header_style="bold")
                table.add_column("ID", style="cyan", justify="right", width=8)
                table.add_column("Name", style="green", min_width=20)
                table.add_column("Location", style="dim", min_width=30)

                for item in items:
                    item_id = str(item.get("id", ""))
                    name = item.get("name", "")
                    location = _get_collection_path(item)

                    table.add_row(item_id, name, location)

                console.print(table)
                console.print()

    except Exception as e:
        _handle_error(e, json_output)
        raise typer.Exit(1) from None
