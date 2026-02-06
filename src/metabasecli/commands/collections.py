"""Collection commands.

Provides commands for managing Metabase collections, including listing,
creating, updating, and archiving collections.
"""

from typing import Annotated, Any

import typer
from rich.table import Table
from rich.tree import Tree

from ..context import get_context
from ..logging import console, error_console
from ..output import handle_api_error, output_json

app = typer.Typer(name="collections", help="Collection operations.")


def _name_matches(name: str, query: str) -> bool:
    """Case-insensitive substring match."""
    return query.lower() in name.lower()


def _find_matches(
    nodes: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    """Recursively find all nodes whose name matches the query.

    Returns a flat list of matching node dicts.
    """
    matches: list[dict[str, Any]] = []
    for node in nodes:
        if _name_matches(node.get("name", ""), query):
            matches.append(node)
        children = node.get("children", [])
        if children:
            matches.extend(_find_matches(children, query))
    return matches


def _collect_ancestor_ids(
    nodes: list[dict[str, Any]],
    target_ids: set[int | str],
) -> set[int | str]:
    """Find all ancestor node IDs that are on the path to any target node.

    Returns the set of IDs (including targets themselves) that should be shown in the tree.
    """
    result: set[int | str] = set()

    def _walk(node: dict[str, Any]) -> bool:
        node_id = node.get("id")
        children = node.get("children", [])

        # Check if this node or any descendant is a target
        is_target = node_id in target_ids
        has_target_descendant = False
        for child in children:
            if _walk(child):
                has_target_descendant = True

        if is_target or has_target_descendant:
            result.add(node_id)
            return True
        return False

    for node in nodes:
        _walk(node)

    return result


def _collect_descendants_to_depth(
    node: dict[str, Any],
    depth: int,
) -> set[int | str]:
    """Collect IDs of all descendants up to `depth` levels below the given node."""
    result: set[int | str] = set()
    if depth <= 0:
        return result

    for child in node.get("children", []):
        child_id = child.get("id")
        result.add(child_id)
        result.update(_collect_descendants_to_depth(child, depth - 1))

    return result


def _build_visible_ids(
    tree: list[dict[str, Any]],
    match_ids: set[int | str],
    levels: int,
) -> set[int | str]:
    """Build the full set of node IDs that should be visible.

    This includes:
    - All ancestors of matched nodes (path to root)
    - The matched nodes themselves
    - `levels` levels of children below each match
    """
    # Ancestors + matches
    visible = _collect_ancestor_ids(tree, match_ids)

    # Children of matches up to `levels` deep
    def _find_and_expand(nodes: list[dict[str, Any]]) -> None:
        for node in nodes:
            node_id = node.get("id")
            if node_id in match_ids:
                visible.update(_collect_descendants_to_depth(node, levels))
            children = node.get("children", [])
            if children:
                _find_and_expand(children)

    _find_and_expand(tree)
    return visible


def _build_path(
    tree: list[dict[str, Any]],
    target_id: int | str,
) -> list[str]:
    """Build the path from root to a node as a list of names."""

    def _walk(nodes: list[dict[str, Any]], path: list[str]) -> list[str] | None:
        for node in nodes:
            current_path = [*path, node.get("name", "")]
            if node.get("id") == target_id:
                return current_path
            children = node.get("children", [])
            if children:
                result = _walk(children, current_path)
                if result is not None:
                    return result
        return None

    return _walk(tree, []) or []


def _render_tree_human(
    tree_data: list[dict[str, Any]],
    match_ids: set[int | str] | None,
    visible_ids: set[int | str] | None,
) -> Tree:
    """Render API tree data as a Rich Tree.

    Args:
        tree_data: The collection tree from the API.
        match_ids: IDs of matched nodes (highlighted), or None to show all.
        visible_ids: IDs of nodes to include, or None to show all.
    """
    root = Tree("[bold]Root Collection[/bold]")

    def _add_children(parent: Tree, children: list[dict[str, Any]]) -> None:
        for child in children:
            child_id = child.get("id")

            # Skip if not in visible set (when filtering)
            if visible_ids is not None and child_id not in visible_ids:
                continue

            name = child.get("name", "Unknown")
            is_match = match_ids is not None and child_id in match_ids

            if is_match:
                label = f"[bold yellow]\\[MATCH][/bold yellow] [green]{name}[/green] [dim](id: {child_id})[/dim]"
            else:
                label = f"[green]{name}[/green] [dim](id: {child_id})[/dim]"

            branch = parent.add(label)

            sub_children = child.get("children", [])
            if sub_children:
                _add_children(branch, sub_children)

    _add_children(root, tree_data)
    return root


def _build_json_tree(
    tree_data: list[dict[str, Any]],
    visible_ids: set[int | str] | None,
    match_ids: set[int | str] | None,
) -> list[dict[str, Any]]:
    """Build a filtered tree structure for JSON output."""
    result = []
    for node in tree_data:
        node_id = node.get("id")
        if visible_ids is not None and node_id not in visible_ids:
            continue

        entry: dict[str, Any] = {
            "id": node_id,
            "name": node.get("name", ""),
        }
        if match_ids is not None:
            entry["is_match"] = node_id in match_ids

        children = node.get("children", [])
        if children:
            filtered_children = _build_json_tree(children, visible_ids, match_ids)
            if filtered_children:
                entry["children"] = filtered_children

        result.append(entry)
    return result


@app.command("tree")
def tree(
    search: Annotated[
        str | None,
        typer.Option("--search", help="Filter collections by name."),
    ] = None,
    levels: Annotated[
        int,
        typer.Option("--levels", "-L", help="How many levels deep to render from matched results."),
    ] = 1,
    exclude_archived: Annotated[
        bool,
        typer.Option("--exclude-archived/--include-archived", help="Exclude archived collections."),
    ] = True,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Display collection hierarchy as a tree."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        tree_data = client.collections.get_tree(exclude_archived=exclude_archived)

        if search:
            # Find matching collections
            matches = _find_matches(tree_data, search)

            if not matches:
                if json_output:
                    output_json(
                        {
                            "query": search,
                            "levels": levels,
                            "matches": [],
                            "tree": [],
                        }
                    )
                else:
                    console.print(f"[dim]No collections matching '{search}' found.[/dim]")
                return

            match_ids = {m.get("id") for m in matches}
            visible_ids = _build_visible_ids(tree_data, match_ids, levels)

            if json_output:
                # Build match details with paths
                match_details = []
                for m in matches:
                    mid = m.get("id")
                    path = _build_path(tree_data, mid)
                    match_entry: dict[str, Any] = {
                        "id": mid,
                        "name": m.get("name", ""),
                        "path": path,
                    }
                    # Include children up to `levels` deep
                    children = m.get("children", [])
                    if children:
                        child_visible = _collect_descendants_to_depth(m, levels)
                        child_visible.add(mid)  # include self for filtering
                        filtered = _build_json_tree(children, child_visible, None)
                        if filtered:
                            match_entry["children"] = filtered

                    match_details.append(match_entry)

                output_json(
                    {
                        "query": search,
                        "levels": levels,
                        "matches": match_details,
                        "tree": _build_json_tree(tree_data, visible_ids, match_ids),
                    }
                )
            else:
                console.print(f"[bold]Search Results ({len(matches)} matches):[/bold]\n")

                rich_tree = _render_tree_human(tree_data, match_ids, visible_ids)
                console.print(rich_tree)

                console.print("\n[bold]Matches:[/bold]")
                for m in matches:
                    mid = m.get("id")
                    path = _build_path(tree_data, mid)
                    path_str = "/" + "/".join(path) if path else "/"
                    console.print(f"  - {m.get('name', '')} [dim](id: {mid}, path: {path_str})[/dim]")
        else:
            # No search - show full tree from root
            if json_output:
                full_tree = _build_json_tree(tree_data, None, None)
                output_json({"tree": full_tree})
            else:
                rich_tree = _render_tree_human(tree_data, None, None)
                console.print(rich_tree)

    except Exception as e:
        handle_api_error(e, json_output, "Collection")
        raise typer.Exit(1) from None


@app.command("get")
def get_collection(
    collection_id: Annotated[str, typer.Argument(help="Collection ID or 'root'.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Get collection details."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        coll_id: int | str = collection_id if collection_id == "root" else int(collection_id)
        collection = client.collections.get(coll_id)

        if json_output:
            output_json(collection)
        else:
            console.print(f"[bold]Collection:[/bold] {collection.get('name', 'Unknown')}")
            console.print(f"[dim]ID:[/dim] {collection.get('id', 'N/A')}")

            if collection.get("description"):
                console.print(f"[dim]Description:[/dim] {collection.get('description')}")

            # Parent info
            parent_id = collection.get("parent_id")
            if parent_id:
                console.print(f"[dim]Parent ID:[/dim] {parent_id}")

            # Path info from ancestors
            ancestors = collection.get("effective_ancestors", [])
            if ancestors:
                path_parts = [a.get("name", "") for a in ancestors if a.get("name")]
                path_parts.append(collection.get("name", ""))
                console.print(f"[dim]Path:[/dim] /{'/'.join(path_parts)}")

            if collection.get("personal_owner_id"):
                console.print(f"[dim]Personal Owner ID:[/dim] {collection.get('personal_owner_id')}")

            if collection.get("archived"):
                console.print("[yellow]This collection is archived[/yellow]")

    except ValueError:
        if json_output:
            output_json({"error": "Invalid collection ID. Must be an integer or 'root'."})
        else:
            error_console.print("[red]Invalid collection ID. Must be an integer or 'root'.[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        handle_api_error(e, json_output, "Collection")
        raise typer.Exit(1) from None


@app.command("items")
def list_items(
    collection_id: Annotated[str, typer.Argument(help="Collection ID or 'root'.")],
    models: Annotated[
        str | None,
        typer.Option("--models", help="Filter by type: card, dashboard, collection, dataset, pulse."),
    ] = None,
    archived: Annotated[
        bool,
        typer.Option("--archived", help="Show archived items."),
    ] = False,
    sort_by: Annotated[
        str | None,
        typer.Option("--sort-by", help="Sort by: name, last_edited_at, last_edited_by, model."),
    ] = None,
    sort_dir: Annotated[
        str | None,
        typer.Option("--sort-dir", help="Sort direction: asc, desc."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List items in a collection."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        coll_id: int | str = collection_id if collection_id == "root" else int(collection_id)

        # Parse models filter
        models_list = None
        if models:
            models_list = [m.strip() for m in models.split(",")]

        items = client.collections.list_items(
            collection_id=coll_id,
            models=models_list,
            archived=archived,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

        if json_output:
            item_list = []
            for item in items:
                item_entry = {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "model": item.get("model"),
                    "description": item.get("description"),
                }
                item_list.append(item_entry)

            output_json({"items": item_list, "total": len(item_list)})
        else:
            if not items:
                console.print("[dim]No items found.[/dim]")
                return

            table = Table(title=f"Items in Collection {collection_id}")
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Type", style="blue")
            table.add_column("Name", style="green")
            table.add_column("Description", style="dim", max_width=50)

            for item in items:
                table.add_row(
                    str(item.get("id", "")),
                    item.get("model", ""),
                    item.get("name", ""),
                    (item.get("description") or "")[:50],
                )

            console.print(table)

    except ValueError:
        if json_output:
            output_json({"error": "Invalid collection ID. Must be an integer or 'root'."})
        else:
            error_console.print("[red]Invalid collection ID. Must be an integer or 'root'.[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        handle_api_error(e, json_output, "Collection")
        raise typer.Exit(1) from None


@app.command("create")
def create_collection(
    name: Annotated[
        str,
        typer.Option("--name", help="Collection name."),
    ],
    description: Annotated[
        str | None,
        typer.Option("--description", help="Description."),
    ] = None,
    parent_id: Annotated[
        int | None,
        typer.Option("--parent-id", help="Parent collection ID."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Create a new collection."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        result = client.collections.create(
            name=name,
            description=description,
            parent_id=parent_id,
        )

        if json_output:
            output_json(
                {
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "action": "created",
                }
            )
        else:
            console.print("[green]Collection created successfully.[/green]")
            console.print(f"[dim]ID:[/dim] {result.get('id')}")
            console.print(f"[dim]Name:[/dim] {result.get('name')}")

    except Exception as e:
        handle_api_error(e, json_output, "Collection")
        raise typer.Exit(1) from None


@app.command("update")
def update_collection(
    collection_id: Annotated[int, typer.Argument(help="Collection ID.")],
    name: Annotated[
        str | None,
        typer.Option("--name", help="New name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description."),
    ] = None,
    parent_id: Annotated[
        int | None,
        typer.Option("--parent-id", help="Move to new parent."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Update a collection."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        result = client.collections.update(
            collection_id=collection_id,
            name=name,
            description=description,
            parent_id=parent_id,
        )

        if json_output:
            output_json(
                {
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "action": "updated",
                }
            )
        else:
            console.print(f"[green]Collection {collection_id} updated successfully.[/green]")

    except Exception as e:
        handle_api_error(e, json_output, "Collection")
        raise typer.Exit(1) from None


@app.command("archive")
def archive_collection(
    collection_id: Annotated[int, typer.Argument(help="Collection ID.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Archive a collection."""
    ctx = get_context()

    try:
        client = ctx.require_auth()
        result = client.collections.archive(collection_id)

        if json_output:
            output_json(
                {
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "archived": True,
                }
            )
        else:
            console.print(f"[green]Collection {collection_id} archived successfully.[/green]")

    except Exception as e:
        handle_api_error(e, json_output, "Collection")
        raise typer.Exit(1) from None
