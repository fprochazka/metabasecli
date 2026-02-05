"""Output formatting and file handling utilities."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


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
