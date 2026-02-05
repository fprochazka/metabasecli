"""Resolve command for parsing Metabase URLs."""

import re
from typing import Annotated
from urllib.parse import urlparse

import typer
from rich.table import Table

from ..client.base import MetabaseAPIError, NotFoundError
from ..context import get_context
from ..logging import console, error_console
from ..output import output_error_json, output_json

# Entity type mappings from URL path to API entity type
URL_PATH_PATTERNS = {
    "question": "card",
    "dashboard": "dashboard",
    "collection": "collection",
    "browse/databases": "database",
    "browse": "database",  # /browse/1/schema/public pattern
}


def parse_metabase_url(url: str) -> tuple[str, int, dict | None] | None:
    """Parse Metabase URL and return (entity_type, entity_id, extra_info) or None.

    Handles both full URLs and paths. Extracts ID from patterns like `123` or `123-slug-text`.

    Args:
        url: Full URL or path like /question/123 or /dashboard/456-my-dashboard

    Returns:
        Tuple of (entity_type, entity_id, extra_info) or None if URL cannot be parsed.
        entity_type is one of: card, dashboard, collection, database
        extra_info may contain additional parsed information like schema name
    """
    # Parse the URL to get the path
    if url.startswith("/"):
        # It's already a path
        path = url
    else:
        # It's a full URL
        parsed = urlparse(url)
        path = parsed.path

    # Remove leading slash and split
    path = path.lstrip("/")
    parts = path.split("/")

    if not parts:
        return None

    # Handle /browse/databases/1 pattern
    if len(parts) >= 3 and parts[0] == "browse" and parts[1] == "databases":
        id_part = parts[2]
        entity_id = _extract_id(id_part)
        if entity_id is not None:
            return ("database", entity_id, None)

    # Handle /browse/1/schema/public pattern (database schema)
    if len(parts) >= 4 and parts[0] == "browse" and parts[2] == "schema":
        id_part = parts[1]
        entity_id = _extract_id(id_part)
        schema_name = parts[3] if len(parts) > 3 else None
        if entity_id is not None:
            return ("database", entity_id, {"schema": schema_name})

    # Handle /browse/1 pattern (just database ID without /databases/)
    if len(parts) >= 2 and parts[0] == "browse":
        id_part = parts[1]
        entity_id = _extract_id(id_part)
        if entity_id is not None:
            return ("database", entity_id, None)

    # Handle standard patterns: /question/123, /dashboard/456, /collection/789
    if len(parts) >= 2:
        entity_path = parts[0]
        id_part = parts[1]

        entity_type = URL_PATH_PATTERNS.get(entity_path)
        if entity_type:
            entity_id = _extract_id(id_part)
            if entity_id is not None:
                return (entity_type, entity_id, None)

    return None


def _extract_id(id_part: str) -> int | None:
    """Extract numeric ID from a URL path part like '123' or '123-slug-text'.

    Args:
        id_part: The path part that may contain an ID

    Returns:
        The numeric ID or None if no valid ID found
    """
    # Match numeric ID, optionally followed by a slug
    match = re.match(r"^(\d+)(?:-.*)?$", id_part)
    if match:
        return int(match.group(1))
    return None


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


def _get_collection_path(collection: dict | None) -> tuple[str, list[str]]:
    """Get the collection path as a string and list.

    Args:
        collection: Collection dict from API response

    Returns:
        Tuple of (path_string, path_list)
    """
    if not collection:
        return ("Root Collection", [])

    # Try to build path from effective_ancestors if available
    ancestors = collection.get("effective_ancestors", [])
    if ancestors:
        path_parts = [a.get("name", "") for a in ancestors if a.get("name")]
        path_parts.append(collection.get("name", ""))
        return ("/" + "/".join(path_parts), path_parts)

    # Fallback to just collection name
    name = collection.get("name", "Root Collection")
    return (f"/{name}" if name != "Root Collection" else "Root Collection", [name] if name != "Root Collection" else [])


def _fetch_card(client, card_id: int) -> dict:
    """Fetch card and format for output."""
    card = client.cards.get(card_id)

    # Get collection info
    collection = card.get("collection")
    collection_path_str, collection_path = _get_collection_path(collection)

    return {
        "entity_type": "card",
        "entity_id": card_id,
        "entity": {
            "id": card_id,
            "name": card.get("name"),
            "description": card.get("description"),
            "collection_id": card.get("collection_id"),
            "collection": {
                "id": collection.get("id") if collection else None,
                "name": collection.get("name") if collection else "Root Collection",
                "path": collection_path,
            }
            if collection
            else None,
            "database_id": card.get("database_id"),
            "database_name": card.get("database", {}).get("name") if card.get("database") else None,
            "display": card.get("display"),
            "query_type": card.get("dataset_query", {}).get("type"),
            "created_at": card.get("created_at"),
            "updated_at": card.get("updated_at"),
        },
        "_raw": card,
        "_collection_path_str": collection_path_str,
    }


def _fetch_dashboard(client, dashboard_id: int) -> dict:
    """Fetch dashboard and format for output."""
    dashboard = client.dashboards.get(dashboard_id)

    # Get collection info
    collection = dashboard.get("collection")
    collection_path_str, collection_path = _get_collection_path(collection)

    # Count dashcards
    dashcards = dashboard.get("dashcards", dashboard.get("ordered_cards", []))
    dashcard_count = len(dashcards) if dashcards else 0

    return {
        "entity_type": "dashboard",
        "entity_id": dashboard_id,
        "entity": {
            "id": dashboard_id,
            "name": dashboard.get("name"),
            "description": dashboard.get("description"),
            "collection_id": dashboard.get("collection_id"),
            "collection": {
                "id": collection.get("id") if collection else None,
                "name": collection.get("name") if collection else "Root Collection",
                "path": collection_path,
            }
            if collection
            else None,
            "dashcard_count": dashcard_count,
            "parameters": dashboard.get("parameters", []),
            "created_at": dashboard.get("created_at"),
            "updated_at": dashboard.get("updated_at"),
        },
        "_raw": dashboard,
        "_collection_path_str": collection_path_str,
    }


def _fetch_collection(client, collection_id: int) -> dict:
    """Fetch collection and format for output."""
    collection = client.collections.get(collection_id)

    # Get parent collection path
    parent = collection.get("parent_id")
    ancestors = collection.get("effective_ancestors", [])
    path_parts = [a.get("name", "") for a in ancestors if a.get("name")]
    path_parts.append(collection.get("name", ""))
    collection_path_str = "/" + "/".join(path_parts) if path_parts else "/"

    return {
        "entity_type": "collection",
        "entity_id": collection_id,
        "entity": {
            "id": collection_id,
            "name": collection.get("name"),
            "description": collection.get("description"),
            "parent_id": parent,
            "path": path_parts,
            "archived": collection.get("archived", False),
            "personal_owner_id": collection.get("personal_owner_id"),
        },
        "_raw": collection,
        "_collection_path_str": collection_path_str,
    }


def _fetch_database(client, database_id: int, schema_name: str | None = None) -> dict:
    """Fetch database and format for output."""
    database = client.databases.get(database_id)

    result = {
        "entity_type": "database",
        "entity_id": database_id,
        "entity": {
            "id": database_id,
            "name": database.get("name"),
            "description": database.get("description"),
            "engine": database.get("engine"),
            "created_at": database.get("created_at"),
            "updated_at": database.get("updated_at"),
        },
        "_raw": database,
        "_collection_path_str": None,
    }

    # If a schema was specified, add it to the output
    if schema_name:
        result["entity"]["schema"] = schema_name

    return result


def resolve_command(
    url: Annotated[str, typer.Argument(help="Metabase URL (full URL or path only).")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Parse a Metabase URL and return information about the referenced entity.

    Supports URLs like:
    - https://metabase.example.com/question/123
    - https://metabase.example.com/dashboard/456-my-dashboard
    - /collection/789
    - /browse/databases/1
    """
    # Parse the URL
    parsed = parse_metabase_url(url)
    if parsed is None:
        if json_output:
            output_error_json(
                code="INVALID_URL",
                message=f"Could not parse URL: {url}",
                details={"url": url},
            )
        else:
            error_console.print(f"[red]Could not parse URL: {url}[/red]")
            error_console.print("[dim]Supported patterns:[/dim]")
            error_console.print("  /question/<id>")
            error_console.print("  /dashboard/<id>")
            error_console.print("  /collection/<id>")
            error_console.print("  /browse/databases/<id>")
            error_console.print("  /browse/<id>/schema/<schema>")
        raise typer.Exit(1)

    entity_type, entity_id, extra_info = parsed

    ctx = get_context()

    try:
        client = ctx.require_auth()

        # Fetch entity based on type
        if entity_type == "card":
            result = _fetch_card(client, entity_id)
        elif entity_type == "dashboard":
            result = _fetch_dashboard(client, entity_id)
        elif entity_type == "collection":
            result = _fetch_collection(client, entity_id)
        elif entity_type == "database":
            schema_name = extra_info.get("schema") if extra_info else None
            result = _fetch_database(client, entity_id, schema_name)
        else:
            if json_output:
                output_error_json(
                    code="UNSUPPORTED_TYPE",
                    message=f"Unsupported entity type: {entity_type}",
                )
            else:
                error_console.print(f"[red]Unsupported entity type: {entity_type}[/red]")
            raise typer.Exit(1)

        # Output the result
        if json_output:
            # Build the JSON output, excluding internal keys
            output_data = {
                "url": url,
                "entity_type": result["entity_type"],
                "entity_id": result["entity_id"],
                "entity": result["entity"],
            }
            output_json(output_data)
        else:
            _print_human_output(url, result)

    except Exception as e:
        _handle_error(e, json_output)
        raise typer.Exit(1) from None


def _print_human_output(url: str, result: dict) -> None:
    """Print human-readable output for the resolved entity."""
    entity = result["entity"]
    entity_type = result["entity_type"]

    console.print(f"\n[bold]URL:[/bold] {url}")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")

    table.add_row("Entity Type", entity_type)
    table.add_row("Entity ID", str(result["entity_id"]))
    table.add_row("Name", entity.get("name") or "[dim]N/A[/dim]")

    if entity.get("description"):
        table.add_row("Description", entity["description"])

    # Collection path (for cards, dashboards, collections)
    collection_path = result.get("_collection_path_str")
    if collection_path:
        table.add_row("Collection", collection_path)

    # Type-specific fields
    if entity_type == "card":
        if entity.get("database_name"):
            table.add_row("Database", f"{entity['database_name']} (id: {entity.get('database_id')})")
        elif entity.get("database_id"):
            table.add_row("Database ID", str(entity["database_id"]))

        if entity.get("display"):
            table.add_row("Display", entity["display"])

        if entity.get("query_type"):
            table.add_row("Query Type", entity["query_type"])

    elif entity_type == "dashboard":
        if entity.get("dashcard_count") is not None:
            table.add_row("Cards", str(entity["dashcard_count"]))

        if entity.get("parameters"):
            param_names = [p.get("name", p.get("slug", "?")) for p in entity["parameters"]]
            table.add_row("Parameters", ", ".join(param_names) if param_names else "[dim]None[/dim]")

    elif entity_type == "collection":
        if entity.get("parent_id"):
            table.add_row("Parent ID", str(entity["parent_id"]))

        if entity.get("archived"):
            table.add_row("Archived", "Yes")

    elif entity_type == "database":
        if entity.get("engine"):
            table.add_row("Engine", entity["engine"])

        if entity.get("schema"):
            table.add_row("Schema", entity["schema"])

    # Timestamps
    if entity.get("updated_at"):
        table.add_row("Last Updated", entity["updated_at"])
    elif entity.get("created_at"):
        table.add_row("Created", entity["created_at"])

    console.print(table)
    console.print()
