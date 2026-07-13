"""Whole-instance ``snapshot`` command: enumerate, fetch, write, prune.

Mirrors Metabase collection content into a deterministic, git-diffable file tree so
AI agents can grep it as local files. The command only *reads* Metabase and writes to a
local directory; restore/round-trip is a non-goal, actionability is a goal (every dumped
object keeps its ids plus a direct ``url``).

The run walks the collection tree, lists each in-scope collection's items, fetches every
card/dashboard body by id (the bulk endpoints omit the fields we need), canonicalizes it
via :mod:`metabasecli.snapshot`, and writes the tree. Stale files from a previous run are
pruned at the very end — but only when the run had zero fetch failures, so a partial run
never deletes the prior snapshot.

Every raw body fetched from the API is also written through to a gitignored raw cache under
``<output>/.metabase-snapshot-cache``. ``--reprocess-only`` then rebuilds the canonical tree
from that cache alone, without any network access — a full run is thousands of API calls, so
re-running canonicalization (e.g. after tweaking a strip rule) must not require re-fetching.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Protocol

import typer

from ..client.base import NotFoundError, PermissionDeniedError
from ..context import get_context
from ..logging import console, error_console
from ..output import handle_api_error, output_json
from ..snapshot import (
    canonicalize_card,
    canonicalize_collection,
    canonicalize_dashboard,
    collection_dir_parts,
    dumps_canonical,
    extract_native_sql,
    object_filename,
)

# Collection-item ``model`` values that are saved questions/models (both fetched via the
# card endpoint) versus dashboards. Everything else (snippets, timelines, pulses, nested
# collections) is out of scope for this command.
_CARD_MODELS = frozenset({"card", "dataset"})

# The ``models`` filter passed to ``list_items`` — the item types this command dumps.
_ITEM_MODELS = ["card", "dataset", "dashboard"]

# Raw-body cache lives inside the output dir so it travels with the snapshot but is kept
# out of git (see :func:`_ensure_cache_gitignore`) and out of prune (see :func:`_prune_stale`).
_CACHE_DIRNAME = ".metabase-snapshot-cache"

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 0.5


class SnapshotCacheError(Exception):
    """The raw cache needed for ``--reprocess-only`` is absent or missing a required file."""


def _with_retry(fn: Callable[[], Any]) -> Any:
    """Call ``fn`` with up to ``_RETRY_ATTEMPTS`` tries and linear backoff.

    Transient errors (connection resets, timeouts, 5xx) are retried; a definitive
    ``NotFoundError``/``PermissionDeniedError`` is not worth retrying and propagates on
    the first try. The final exception propagates so the caller can record the failure.
    """
    last_exc: Exception | None = None
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            return fn()
        except (NotFoundError, PermissionDeniedError):
            raise
        except Exception as exc:
            last_exc = exc
            if attempt < _RETRY_ATTEMPTS:
                time.sleep(_RETRY_BASE_DELAY * attempt)
    assert last_exc is not None
    raise last_exc


class SnapshotSource(Protocol):
    """Source of the raw Metabase bodies a snapshot is built from.

    Two implementations back it: :class:`ApiSource` fetches from the live instance (and
    writes each body through to the raw cache), while :class:`CacheSource` reads those cached
    bodies back with no network access. Both expose the same four ops so the canonicalize →
    write → prune pipeline is identical regardless of where the bodies come from.
    """

    def tree(self) -> list[dict[str, Any]]: ...

    def items(self, collection_id: int | str) -> list[dict[str, Any]]: ...

    def card(self, card_id: int) -> dict[str, Any]: ...

    def dashboard(self, dashboard_id: int) -> dict[str, Any]: ...


def _write_cache_json(path: Path, obj: Any) -> None:
    """Persist a raw body to the cache (canonical serialization; content is gitignored)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_canonical(obj), encoding="utf-8")


def _read_cache_json(path: Path) -> Any:
    """Read a cached raw body, raising :class:`SnapshotCacheError` if the file is absent."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SnapshotCacheError(f"missing cache file {path}") from None
    return json.loads(text)


class ApiSource:
    """Fetch raw bodies from the live Metabase API, writing each through to the raw cache.

    Every body the snapshot reads is persisted under ``cache_dir`` so a normal run always
    leaves a complete, fresh cache that a later ``--reprocess-only`` run can rebuild from.
    """

    def __init__(self, client: Any, cache_dir: Path) -> None:
        self._client = client
        self._cache_dir = cache_dir

    def tree(self) -> list[dict[str, Any]]:
        data = _with_retry(self._client.collections.get_tree)
        _write_cache_json(self._cache_dir / "tree.json", data)
        return data

    def items(self, collection_id: int | str) -> list[dict[str, Any]]:
        data = _with_retry(lambda: self._client.collections.list_items(collection_id, models=_ITEM_MODELS))
        _write_cache_json(self._cache_dir / "items" / f"{collection_id}.json", data)
        return data

    def card(self, card_id: int) -> dict[str, Any]:
        data = _with_retry(lambda: self._client.cards.get(card_id, legacy_mbql=True))
        _write_cache_json(self._cache_dir / "cards" / f"{card_id}.json", data)
        return data

    def dashboard(self, dashboard_id: int) -> dict[str, Any]:
        data = _with_retry(lambda: self._client.dashboards.get(dashboard_id))
        _write_cache_json(self._cache_dir / "dashboards" / f"{dashboard_id}.json", data)
        return data


class CacheSource:
    """Rebuild the snapshot purely from the raw cache written by a prior API-backed run.

    Reads exactly the paths :class:`ApiSource` writes, with no network access. A missing
    per-object file surfaces as a :class:`SnapshotCacheError` the caller records as a fetch
    failure (so a partial cache never silently drops objects); a missing ``tree.json`` means
    there is no usable cache at all and is reported up front.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir

    def tree(self) -> list[dict[str, Any]]:
        path = self._cache_dir / "tree.json"
        if not path.exists():
            raise SnapshotCacheError(f"no snapshot cache at {self._cache_dir}; run a full snapshot first")
        return _read_cache_json(path)

    def items(self, collection_id: int | str) -> list[dict[str, Any]]:
        return _read_cache_json(self._cache_dir / "items" / f"{collection_id}.json")

    def card(self, card_id: int) -> dict[str, Any]:
        return _read_cache_json(self._cache_dir / "cards" / f"{card_id}.json")

    def dashboard(self, dashboard_id: int) -> dict[str, Any]:
        return _read_cache_json(self._cache_dir / "dashboards" / f"{dashboard_id}.json")


def _ensure_cache_gitignore(cache_dir: Path) -> None:
    """Write ``<cache_dir>/.gitignore`` = ``*`` so git ignores the entire raw cache.

    A single ``*`` line makes git ignore every path in the cache dir (including the
    ``.gitignore`` itself), so ``--commit``'s ``git add -A`` never stages raw bodies — and the
    user's own top-level ``.gitignore`` is left untouched.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / ".gitignore").write_text("*\n", encoding="utf-8")


def _flatten_tree(nodes: list[dict[str, Any]], by_id: dict[int, dict[str, Any]]) -> None:
    """Populate ``by_id`` with every node in the tree, keyed by id.

    Keeps *all* nodes (personal and Trash included) so that ancestor-id path resolution in
    :func:`collection_dir_parts` always finds a name, even for an in-scope collection whose
    ancestor is out of scope.
    """
    for node in nodes:
        node_id = node.get("id")
        if isinstance(node_id, int):
            by_id[node_id] = node
        _flatten_tree(node.get("children", []) or [], by_id)


def _location_ids(location: str | None) -> list[int]:
    """Parse the ancestor ids out of a collection ``location`` (``/a/b/`` id-chain)."""
    ids: list[int] = []
    for token in (location or "/").strip("/").split("/"):
        if token:
            ids.append(int(token))
    return ids


def _subtree_ids(by_id: dict[int, dict[str, Any]], collection_id: int) -> set[int]:
    """Ids of the ``--collection-id`` subtree, computed offline from the loaded tree.

    A collection is in the subtree if it *is* ``collection_id`` or ``collection_id`` appears
    in its ``location`` ancestor chain. Derived from ``by_id`` alone so ``--reprocess-only``
    (and a normal run) needs no extra network round-trip to scope the run.
    """
    ids = {collection_id}
    for cid, node in by_id.items():
        if collection_id in _location_ids(node.get("location")):
            ids.add(cid)
    return ids


def _in_scope_collections(
    by_id: dict[int, dict[str, Any]],
    scope_ids: set[int] | None,
    include_personal: bool,
) -> list[dict[str, Any]]:
    """Select the collections to dump, sorted by id for stable ordering.

    Always drops Trash (``type == "trash"``); drops personal collections — a user's
    personal root *and* everything nested under it — unless ``include_personal``; and, when
    ``scope_ids`` is given (``--collection-id`` subtree), keeps only ids in that set.
    """
    personal_ids = {cid for cid, node in by_id.items() if node.get("personal_owner_id") is not None}

    def _is_personal(cid: int, node: dict[str, Any]) -> bool:
        # A collection is personal if it is a user's personal root (``personal_owner_id``
        # set) or nests under one. The API only stamps ``personal_owner_id`` on the root,
        # so nested personal sub-collections must be caught via their ``location`` chain.
        if cid in personal_ids:
            return True
        return any(ancestor_id in personal_ids for ancestor_id in _location_ids(node.get("location")))

    selected: list[dict[str, Any]] = []
    for cid in sorted(by_id):
        node = by_id[cid]
        if scope_ids is not None and cid not in scope_ids:
            continue
        if node.get("type") == "trash":
            continue
        if not include_personal and _is_personal(cid, node):
            continue
        selected.append(node)
    return selected


def _write_file(path: Path, text: str, written: set[Path]) -> None:
    """Write ``text`` to ``path`` (creating parents) and record it as written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    written.add(path.resolve())


def _process_items(
    items: list[dict[str, Any]],
    base_dir: Path,
    coll_id: int | None,
    *,
    source: SnapshotSource,
    base_url: str,
    counters: dict[str, int],
    written: set[Path],
    failures: list[dict[str, Any]],
) -> None:
    """Fetch, canonicalize, and write every card/dashboard in ``items``.

    Cards/models land in ``<base_dir>/cards/`` (with a companion ``.sql`` for native
    queries), dashboards in ``<base_dir>/dashboards/``. A per-object body that cannot be
    obtained (API failure after retries, or a missing cache file under ``--reprocess-only``)
    is appended to ``failures`` and skipped; the run continues.
    """
    for item in sorted(items, key=lambda it: it.get("id") or 0):
        model = item.get("model")
        item_id = item.get("id")
        if not isinstance(item_id, int):
            continue

        if model in _CARD_MODELS:
            try:
                card = source.card(item_id)
            except Exception as exc:
                failures.append({"collection_id": coll_id, "model": "card", "id": item_id, "error": str(exc)})
                continue
            basename = object_filename(card)
            _write_file(
                base_dir / "cards" / f"{basename}.json", dumps_canonical(canonicalize_card(card, base_url)), written
            )
            sql = extract_native_sql(card)
            if sql is not None:
                _write_file(base_dir / "cards" / f"{basename}.sql", sql if sql.endswith("\n") else sql + "\n", written)
            counters["cards"] += 1

        elif model == "dashboard":
            try:
                dash = source.dashboard(item_id)
            except Exception as exc:
                failures.append({"collection_id": coll_id, "model": "dashboard", "id": item_id, "error": str(exc)})
                continue
            basename = object_filename(dash)
            _write_file(
                base_dir / "dashboards" / f"{basename}.json",
                dumps_canonical(canonicalize_dashboard(dash, base_url)),
                written,
            )
            counters["dashboards"] += 1


def _prune_stale(output_dir: Path, written: set[Path]) -> list[Path]:
    """Delete every ``*.json``/``*.sql`` under ``output_dir`` not written this run.

    Then removes directories left empty, deepest-first. Two subtrees are never descended
    into or touched: ``.git`` (the output may itself be a git mirror repo) and the raw cache
    (``.metabase-snapshot-cache``) — the cache is full of ``.json`` bodies that this run did
    not "write" in the snapshot sense, so descending it would wrongly delete the whole cache.
    """
    removed: list[Path] = []
    dirs_seen: list[Path] = []
    for root, dirs, files in os.walk(output_dir):
        if ".git" in dirs:
            dirs.remove(".git")
        if _CACHE_DIRNAME in dirs:
            dirs.remove(_CACHE_DIRNAME)
        root_path = Path(root)
        if root_path != output_dir:
            dirs_seen.append(root_path)
        for name in files:
            if name.endswith((".json", ".sql")):
                path = root_path / name
                if path.resolve() not in written:
                    path.unlink()
                    removed.append(path)

    for path in sorted(dirs_seen, key=lambda p: len(p.parts), reverse=True):
        try:
            if not any(path.iterdir()):
                path.rmdir()
        except OSError:
            pass

    return removed


class GitError(Exception):
    """A git operation on the snapshot output dir failed (e.g. it is not a repository)."""


def _git(output_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``git -C <output_dir> <args>`` capturing output, without raising on failure.

    Output is captured (never inherited) so git's own chatter can't corrupt ``--json`` stdout;
    callers inspect ``returncode`` or hand off to :func:`_git_checked`.
    """
    return subprocess.run(["git", "-C", str(output_dir), *args], capture_output=True, text=True)


def _git_checked(output_dir: Path, *args: str) -> None:
    """Run a git command that must succeed, raising :class:`GitError` with its stderr if not."""
    proc = _git(output_dir, *args)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise GitError(f"git {' '.join(args)} failed: {detail}")


def _git_snapshot(output_dir: Path, *, commit: bool, push: bool) -> dict[str, Any]:
    """Stage/commit/push the snapshot *output dir* — the user's git mirror repo, not this repo.

    Mirrors the reference mirror scripts: ``git add -A``, skip the commit when nothing is
    staged, else commit as ``v<timestamp>``, then optionally ``git push``. The output dir must
    already be a git repository (the user owns the mirror repo; this never inits one). The
    caller invokes this only after a fully successful run (zero fetch failures), so a partial
    mirror is never committed.

    Returns ``{"committed": <tag or None>, "pushed": <bool>}``.
    """
    if _git(output_dir, "rev-parse", "--is-inside-work-tree").returncode != 0:
        raise GitError(
            f"{output_dir} is not a git repository — create the mirror repo (git init) before --commit/--push."
        )

    result: dict[str, Any] = {"committed": None, "pushed": False}

    if commit:
        _git_checked(output_dir, "add", "-A")
        nothing_staged = _git(output_dir, "diff", "--cached", "--quiet").returncode == 0
        if not nothing_staged:
            stamp = "v" + time.strftime("%Y%m%d%H%M%S")
            _git_checked(output_dir, "commit", "-m", stamp)
            result["committed"] = stamp

    if push:
        _git_checked(output_dir, "push")
        result["pushed"] = True

    return result


def snapshot_command(
    output: Annotated[str, typer.Option("--output", help="Directory to write the snapshot tree into.")],
    collection_id: Annotated[
        int | None,
        typer.Option("--collection-id", help="Restrict to this collection and its descendants."),
    ] = None,
    include_personal: Annotated[
        bool,
        typer.Option("--include-personal", help="Include personal collections (default: shared only)."),
    ] = False,
    reprocess_only: Annotated[
        bool,
        typer.Option(
            "--reprocess-only",
            help="Rebuild the tree from the raw cache of a prior run, with no API calls.",
        ),
    ] = False,
    commit: Annotated[
        bool,
        typer.Option("--commit", help="git add -A and commit the output dir as v<timestamp> after a clean run."),
    ] = False,
    push: Annotated[
        bool,
        typer.Option("--push", help="git push the output dir after committing (requires it to be a git repo)."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Mirror shared Metabase collection content into a deterministic file tree.

    Walks the collection tree, dumps each in-scope collection's ``_collection.json`` plus
    its cards (with native ``.sql`` companions) and dashboards, then prunes files left over
    from a previous run. Prune is skipped and the exit code is non-zero if any object failed
    to fetch, so a partial run never deletes the prior snapshot.

    Every fetched body is also cached under ``<output>/.metabase-snapshot-cache`` (gitignored).
    ``--reprocess-only`` rebuilds the tree from that cache with no network access — useful for
    re-running canonicalization without repeating a full run's thousands of API calls.

    ``--commit``/``--push`` version the *output dir* itself (which must be a git mirror repo the
    user owns) as ``v<timestamp>``; they run only after a clean run — a partial mirror with
    fetch failures is never committed.
    """
    ctx = get_context()

    output_dir = Path(output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / _CACHE_DIRNAME

    # Pick the raw-body source and load the collection tree. ``--reprocess-only`` reads the
    # cache alone (no auth, no network); a normal run fetches from the API and writes through
    # to the cache. A missing/incomplete cache (no ``tree.json``) fails clearly here.
    try:
        if reprocess_only:
            config = ctx.config
            if config is None:
                raise SnapshotCacheError("no profile configured; run 'metabase auth login' first")
            base_url = config.url
            source: SnapshotSource = CacheSource(cache_dir)
        else:
            client = ctx.require_auth()
            base_url = ctx.config.url
            source = ApiSource(client, cache_dir)
        tree = source.tree()
    except Exception as e:
        handle_api_error(e, json_output, "Snapshot")
        raise typer.Exit(1) from None

    # Keep the cache invisible to git so a mirror repo's ``git add -A`` never stages raw bodies.
    _ensure_cache_gitignore(cache_dir)

    by_id: dict[int, dict[str, Any]] = {}
    _flatten_tree(tree, by_id)
    scope_ids = _subtree_ids(by_id, collection_id) if collection_id is not None else None
    collections = _in_scope_collections(by_id, scope_ids, include_personal)

    written: set[Path] = set()
    failures: list[dict[str, Any]] = []
    counters: dict[str, int] = {"collections": 0, "cards": 0, "dashboards": 0}

    for node in collections:
        cid = node["id"]
        coll_dir = output_dir.joinpath(*collection_dir_parts(node, by_id))
        _write_file(coll_dir / "_collection.json", dumps_canonical(canonicalize_collection(node, base_url)), written)
        counters["collections"] += 1

        try:
            items = source.items(cid)
        except Exception as exc:
            failures.append({"collection_id": cid, "model": "items", "id": None, "error": str(exc)})
            continue
        _process_items(
            items,
            coll_dir,
            cid,
            source=source,
            base_url=base_url,
            counters=counters,
            written=written,
            failures=failures,
        )

    # Root-level items (``collection_id == null``) live at the tree root, not under any
    # collection dir. They are out of scope for a ``--collection-id`` subtree run.
    if collection_id is None:
        try:
            root_items = source.items("root")
        except Exception as exc:
            failures.append({"collection_id": None, "model": "items", "id": None, "error": str(exc)})
            root_items = []
        _process_items(
            root_items,
            output_dir,
            None,
            source=source,
            base_url=base_url,
            counters=counters,
            written=written,
            failures=failures,
        )

    pruned: list[Path] = _prune_stale(output_dir, written) if not failures else []

    # Git ops act on the output dir (the mirror repo), never this repo, and only after a clean
    # run — the command already exits non-zero on failures, so a partial mirror is left as-is.
    git_result: dict[str, Any] | None = None
    git_error: str | None = None
    if (commit or push) and not failures:
        try:
            git_result = _git_snapshot(output_dir, commit=commit, push=push)
        except GitError as exc:
            git_error = str(exc)

    if json_output:
        payload: dict[str, Any] = {
            "output": str(output_dir),
            "collections": counters["collections"],
            "cards": counters["cards"],
            "dashboards": counters["dashboards"],
            "pruned": len(pruned),
            "failures": failures,
        }
        if commit or push:
            payload["git"] = {"error": git_error} if git_error else git_result
        output_json(payload)
    else:
        console.print(f"Snapshot written to {output_dir}")
        console.print(f"  collections: {counters['collections']}")
        console.print(f"  cards:       {counters['cards']}")
        console.print(f"  dashboards:  {counters['dashboards']}")
        if failures:
            console.print("  pruned:      skipped (fetch failures present)")
            error_console.print(f"[red]{len(failures)} fetch failure(s):[/red]")
            for failure in failures:
                error_console.print(
                    f"[red]  {failure['model']} {failure['id']} "
                    f"(collection {failure['collection_id']}): {failure['error']}[/red]"
                )
        else:
            console.print(f"  pruned:      {len(pruned)}")
            if git_error:
                error_console.print(f"[red]git: {git_error}[/red]")
            elif git_result is not None:
                if git_result["committed"]:
                    console.print(f"  committed:   {git_result['committed']}")
                elif commit:
                    console.print("  committed:   nothing to commit")
                if git_result["pushed"]:
                    console.print("  pushed:      yes")

    if failures or git_error:
        raise typer.Exit(1)
