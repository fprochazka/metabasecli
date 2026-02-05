"""Database-related models."""

from dataclasses import dataclass, field


@dataclass
class Field:
    """A field (column) in a Metabase table."""

    id: int
    name: str
    display_name: str
    base_type: str
    semantic_type: str | None = None
    description: str | None = None
    visibility_type: str = "normal"
    active: bool = True
    extra: dict = field(default_factory=dict)


@dataclass
class Table:
    """A table in a Metabase database."""

    id: int
    name: str
    display_name: str
    schema: str | None = None
    description: str | None = None
    visibility_type: str = "normal"
    active: bool = True
    fields: list[Field] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


@dataclass
class Database:
    """A Metabase database connection."""

    id: int
    name: str
    engine: str
    description: str | None = None
    is_sample: bool = False
    tables_count: int = 0
    tables: list[Table] = field(default_factory=list)
    extra: dict = field(default_factory=dict)
