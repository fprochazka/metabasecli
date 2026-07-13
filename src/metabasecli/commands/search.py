"""Search command.

Provides global search functionality across all Metabase entities including
cards, dashboards, collections, databases, tables, and more.
"""

from collections import defaultdict
from typing import Annotated

import typer

from ..constants import SEARCHABLE_MODELS
from ..context import get_context
from ..logging import console
from ..output import filter_items_by_collections, get_collection_path, handle_api_error, output_json


def _print_model_group(model_type: str, items: list) -> None:
    """Print a bullet list of search results for a single model type."""
    console.print(f"[bold cyan]{model_type.upper()}S ({len(items)}):[/bold cyan]")

    for item in items:
        name = item.get("name", "Unknown")
        item_id = item.get("id", "")
        location = get_collection_path(item)
        description = (item.get("description") or "").strip()

        parts = [f"id: {item_id}", f"type: {model_type}"]
        if location:
            parts.append(f"location: {location}")

        line = f"* {name} ({', '.join(parts)})"
        if description:
            line += f" - {description[:80]}"
        console.print(line)

    console.print()


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

        if collection_id is not None:
            # The server-side `collection` filter is a no-op on Metabase 0.48; enforce it
            # over the returned page for subtree-consistent results on both versions.
            allowed_ids = client.collections.get_descendant_ids(collection_id)
            filtered = filter_items_by_collections(data, allowed_ids)
            if len(filtered) != len(data):
                # Items were dropped, so the server did not filter (0.48); its `total`
                # counts the unfiltered result set, so report the count we can vouch for.
                total = len(filtered)
            data = filtered

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
            console.print(f"[bold]Search results for '[/bold]{query}[bold]'[/bold]")
            console.print(f"[dim]Found {total} results[/dim]\n")

            # Print counts by type
            type_counts = []
            for model_type, items in sorted(grouped.items()):
                type_counts.append(f"{model_type}: {len(items)}")
            console.print(f"[dim]By type: {', '.join(type_counts)}[/dim]\n")

            # Print each group in defined order
            for model_type in SEARCHABLE_MODELS:
                if model_type not in grouped:
                    continue
                _print_model_group(model_type, grouped[model_type])

            # Print any remaining types not in the predefined order
            remaining = set(grouped.keys()) - set(SEARCHABLE_MODELS)
            for model_type in sorted(remaining):
                _print_model_group(model_type, grouped[model_type])

    except Exception as e:
        handle_api_error(e, json_output)
        raise typer.Exit(1) from None
