"""Output formatting and file handling utilities."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .client.base import MetabaseAPIError, NotFoundError
from .logging import console, error_console


def create_export_dir() -> Path:
    """Create and return a timestamped export directory.

    Creates a directory like /tmp/metabase-20260205-183500/
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dir_path = Path(f"/tmp/metabase-{timestamp}")
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def write_json_file(dir_path: Path, filename: str, data: dict) -> Path:
    """Write data to a JSON file.

    Args:
        dir_path: Directory to write to.
        filename: Name of the file (without path).
        data: Data to write.

    Returns:
        Full path to the written file.
    """
    file_path = dir_path / filename
    file_path.write_text(json.dumps(data, indent=2, default=str))
    return file_path


def write_export_file(
    dir_path: Path,
    filename: str,
    data: dict,
    export_type: str,
    source_info: dict | None = None,
) -> Path:
    """Write an export file with standard envelope.

    Args:
        dir_path: Directory to write to.
        filename: Name of the file (without path).
        data: The main data to export.
        export_type: Type of export ("card", "dashboard", etc.).
        source_info: Optional source information dict.

    Returns:
        Full path to the written file.
    """
    export_data = {
        "export_version": "1.0",
        "export_timestamp": datetime.now().isoformat() + "Z",
        "type": export_type,
        "source": source_info or {},
        export_type: data,
    }
    return write_json_file(dir_path, filename, export_data)


def write_csv_file(
    dir_path: Path,
    filename: str,
    headers: list[str],
    rows: list[list[Any]],
) -> Path:
    """Write data to a CSV file.

    Args:
        dir_path: Directory to write to.
        filename: Name of the file (without path).
        headers: Column headers.
        rows: Data rows.

    Returns:
        Full path to the written file.
    """
    import csv

    file_path = dir_path / filename
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return file_path


def output_json(data: dict, success: bool = True) -> None:
    """Output data as JSON to stdout.

    Wraps data in the standard response envelope.
    """
    envelope = {
        "success": success,
        "data": data,
        "meta": {
            "timestamp": datetime.now().isoformat() + "Z",
        },
    }
    console.print_json(json.dumps(envelope, default=str))


def output_error_json(
    code: str,
    message: str,
    details: dict | None = None,
) -> None:
    """Output an error as JSON to stdout."""
    envelope = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details:
        envelope["error"]["details"] = details
    console.print_json(json.dumps(envelope, default=str))


def handle_api_error(e: Exception, json_output: bool, entity_name: str = "Resource") -> None:
    """Handle API errors consistently across all commands.

    Args:
        e: The exception that was raised.
        json_output: Whether to output in JSON format.
        entity_name: Name of the entity type for human-readable messages.
    """
    if isinstance(e, NotFoundError):
        if json_output:
            output_error_json(
                code="NOT_FOUND",
                message=str(e),
                details={"status_code": e.status_code} if e.status_code else None,
            )
        else:
            error_console.print(f"[red]{entity_name} not found: {e}[/red]")
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


def get_collection_path(item_or_collection: dict) -> str:
    """Get the collection path as a human-readable string.

    This works for both:
    - Items that have a 'collection' field (cards, dashboards)
    - Collection objects directly

    Args:
        item_or_collection: A dict containing collection info

    Returns:
        Human-readable collection path string
    """
    # Check if this is an item with a collection field or a collection itself
    collection = item_or_collection.get("collection") or item_or_collection
    if not collection or not isinstance(collection, dict):
        return "Root Collection"

    # Try to build path from effective_ancestors if available
    ancestors = collection.get("effective_ancestors", [])
    if ancestors:
        path_parts = [a.get("name", "") for a in ancestors if a.get("name")]
        path_parts.append(collection.get("name", ""))
        return " / ".join(path_parts)

    # Fallback to just collection name
    return collection.get("name", "Root Collection")
