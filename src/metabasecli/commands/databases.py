"""Database commands."""

from typing import Annotated

import typer
from rich.table import Table
from rich.tree import Tree

from ..context import get_context
from ..logging import console
from ..output import handle_api_error, output_json

app = typer.Typer(name="databases", help="Database operations.")


@app.command("list")
def list_databases(
    include_tables: Annotated[
        bool,
        typer.Option("--include-tables", help="Include table information."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List all databases."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        databases = client.databases.list(include_tables=include_tables)

        if json_output:
            # Build output data
            db_list = []
            for db in databases:
                db_entry = {
                    "id": db.get("id"),
                    "name": db.get("name"),
                    "engine": db.get("engine"),
                }
                # Add tables count if we have tables
                if include_tables and "tables" in db:
                    db_entry["tables_count"] = len(db.get("tables", []))
                elif "tables" in db and isinstance(db["tables"], int):
                    db_entry["tables_count"] = db["tables"]

                db_list.append(db_entry)

            output_json({"databases": db_list})
        else:
            # Human-readable table output
            table = Table(title="Databases")
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Name", style="green")
            table.add_column("Engine", style="blue")
            if include_tables:
                table.add_column("Tables", justify="right")

            for db in databases:
                row = [
                    str(db.get("id", "")),
                    db.get("name", ""),
                    db.get("engine", ""),
                ]
                if include_tables:
                    tables = db.get("tables", [])
                    if isinstance(tables, list):
                        row.append(str(len(tables)))
                    else:
                        row.append(str(tables))
                table.add_row(*row)

            console.print(table)

    except Exception as e:
        handle_api_error(e, json_output, "Database")
        raise typer.Exit(1) from None


@app.command("get")
def get_database(
    database_id: Annotated[int, typer.Argument(help="Database ID.")],
    include_tables: Annotated[
        bool,
        typer.Option("--include-tables", help="Include tables."),
    ] = False,
    include_fields: Annotated[
        bool,
        typer.Option("--include-fields", help="Include tables and fields."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Get database details."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        database = client.databases.get(
            database_id,
            include_tables=include_tables,
            include_fields=include_fields,
        )

        if json_output:
            output_json(database)
        else:
            # Human-readable output
            console.print(f"[bold]Database:[/bold] {database.get('name', 'Unknown')}")
            console.print(f"[dim]ID:[/dim] {database.get('id', 'N/A')}")
            console.print(f"[dim]Engine:[/dim] {database.get('engine', 'N/A')}")

            if database.get("description"):
                console.print(f"[dim]Description:[/dim] {database.get('description')}")

            if database.get("is_sample"):
                console.print("[yellow]This is a sample database[/yellow]")

            # Show tables if included
            tables = database.get("tables", [])
            if tables and isinstance(tables, list):
                console.print(f"\n[bold]Tables ({len(tables)}):[/bold]")
                for t in tables:
                    table_name = t.get("name", "Unknown")
                    schema = t.get("schema", "")
                    display = f"  - {schema}.{table_name}" if schema else f"  - {table_name}"
                    console.print(display)

                    # Show fields if included
                    fields = t.get("fields", [])
                    if fields and isinstance(fields, list):
                        for f in fields:
                            field_name = f.get("name", "Unknown")
                            base_type = f.get("base_type", "")
                            semantic_type = f.get("semantic_type", "")
                            type_info = f"{base_type} ({semantic_type})" if semantic_type else base_type
                            console.print(f"      {field_name}: {type_info}")

    except Exception as e:
        handle_api_error(e, json_output, "Database")
        raise typer.Exit(1) from None


@app.command("metadata")
def get_metadata(
    database_id: Annotated[int, typer.Argument(help="Database ID.")],
    include_hidden: Annotated[
        bool,
        typer.Option("--include-hidden", help="Include hidden tables and fields."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Get complete database metadata including all tables and fields."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        metadata = client.databases.get_metadata(database_id, include_hidden=include_hidden)

        if json_output:
            output_json(metadata)
        else:
            # Human-readable tree output
            db_name = metadata.get("name", "Unknown Database")
            console.print(f"[bold]Database Metadata:[/bold] {db_name}")
            console.print(f"[dim]ID:[/dim] {metadata.get('id', 'N/A')}")
            console.print(f"[dim]Engine:[/dim] {metadata.get('engine', 'N/A')}")
            console.print()

            # Build a tree of schemas > tables > fields
            tables = metadata.get("tables", [])
            if not tables:
                console.print("[dim]No tables found[/dim]")
                return

            # Group tables by schema
            schemas: dict[str, list] = {}
            for t in tables:
                schema_name = t.get("schema") or "(no schema)"
                if schema_name not in schemas:
                    schemas[schema_name] = []
                schemas[schema_name].append(t)

            # Create tree
            tree = Tree(f"[bold]{db_name}[/bold]")

            for schema_name in sorted(schemas.keys()):
                schema_tables = schemas[schema_name]
                schema_branch = tree.add(f"[cyan]{schema_name}[/cyan]")

                for t in sorted(schema_tables, key=lambda x: x.get("name", "")):
                    table_name = t.get("display_name") or t.get("name", "Unknown")
                    table_branch = schema_branch.add(f"[green]{table_name}[/green]")

                    fields = t.get("fields", [])
                    for f in fields:
                        field_name = f.get("display_name") or f.get("name", "Unknown")
                        base_type = f.get("base_type", "")
                        # Simplify the type for display
                        short_type = base_type.replace("type/", "") if base_type else ""
                        semantic = f.get("semantic_type")
                        if semantic:
                            semantic = semantic.replace("type/", "")
                            table_branch.add(f"{field_name} [dim]{short_type}[/dim] [blue]({semantic})[/blue]")
                        else:
                            table_branch.add(f"{field_name} [dim]{short_type}[/dim]")

            console.print(tree)

    except Exception as e:
        handle_api_error(e, json_output, "Database")
        raise typer.Exit(1) from None


@app.command("schemas")
def list_schemas(
    database_id: Annotated[int, typer.Argument(help="Database ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List all schemas in a database."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        schemas = client.databases.list_schemas(database_id)

        if json_output:
            output_json({"schemas": schemas})
        else:
            if not schemas:
                console.print("[dim]No schemas found[/dim]")
                return

            console.print(f"[bold]Schemas ({len(schemas)}):[/bold]")
            for schema in schemas:
                console.print(f"  - {schema}")

    except Exception as e:
        handle_api_error(e, json_output, "Database")
        raise typer.Exit(1) from None
