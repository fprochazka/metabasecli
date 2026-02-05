"""Database-related models.

Contains dataclasses for Metabase database, table, and field objects.
"""

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Field", "Table", "Database"]


@dataclass
class Field:
    """A field (column) in a Metabase table."""

    id: int
    name: str
    display_name: str
    base_type: str
    table_id: int | None = None
    semantic_type: str | None = None
    description: str | None = None
    visibility_type: str = "normal"
    active: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Field":
        """Create a Field from an API response dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            base_type=data.get("base_type", ""),
            table_id=data.get("table_id"),
            semantic_type=data.get("semantic_type"),
            description=data.get("description"),
            visibility_type=data.get("visibility_type", "normal"),
            active=data.get("active", True),
            extra={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "id",
                    "name",
                    "display_name",
                    "base_type",
                    "table_id",
                    "semantic_type",
                    "description",
                    "visibility_type",
                    "active",
                }
            },
        )


@dataclass
class Table:
    """A table in a Metabase database."""

    id: int
    name: str
    display_name: str
    db_id: int | None = None
    schema: str | None = None
    description: str | None = None
    visibility_type: str = "normal"
    active: bool = True
    fields: list[Field] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Table":
        """Create a Table from an API response dictionary."""
        fields_data = data.get("fields", [])
        fields = [Field.from_dict(f) for f in fields_data] if fields_data else []

        return cls(
            id=data["id"],
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            db_id=data.get("db_id"),
            schema=data.get("schema"),
            description=data.get("description"),
            visibility_type=data.get("visibility_type", "normal"),
            active=data.get("active", True),
            fields=fields,
            extra={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "id",
                    "name",
                    "display_name",
                    "db_id",
                    "schema",
                    "description",
                    "visibility_type",
                    "active",
                    "fields",
                }
            },
        )


@dataclass
class Database:
    """A Metabase database connection."""

    id: int
    name: str
    engine: str
    description: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    is_sample: bool = False
    tables_count: int = 0
    tables: list[Table] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Database":
        """Create a Database from an API response dictionary."""
        tables_data = data.get("tables", [])
        tables = [Table.from_dict(t) for t in tables_data] if tables_data else []

        return cls(
            id=data["id"],
            name=data["name"],
            engine=data.get("engine", ""),
            description=data.get("description"),
            details=data.get("details", {}),
            is_sample=data.get("is_sample", False),
            tables_count=len(tables) if tables else data.get("tables", 0),
            tables=tables,
            extra={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "id",
                    "name",
                    "engine",
                    "description",
                    "details",
                    "is_sample",
                    "tables",
                }
            },
        )
