"""Pure helpers for the whole-instance ``snapshot`` mirror.

The snapshot command dumps Metabase content into a git-diffable file tree so a
semi-daily re-run diffs only on *real* content changes. Everything here is a pure
transform (no network, no filesystem) so it stays trivially testable and so the
canonicalization can be re-applied to cached bodies without re-fetching.

Two ideas drive the code:

- **Determinism.** Objects are dumped with sorted keys and a trailing newline, and
  runtime churn (view counters, cache timestamps, per-request permission flags,
  embedded snapshots duplicated elsewhere) is stripped so it never shows up in a diff.
- **Whitelist-by-exclusion.** Canonicalization starts from the *full* object and only
  removes a known strip-set (plus a couple of normalizations), so newly introduced
  API fields survive into the snapshot instead of being silently dropped.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any

__all__ = [
    "slugify",
    "collection_dir_parts",
    "object_filename",
    "object_url",
    "canonicalize_card",
    "canonicalize_dashboard",
    "canonicalize_collection",
    "extract_native_sql",
    "dumps_canonical",
]

# Card fields dropped as noise or redundancy: usage counters, cache/version stamps, an
# embedded copy of the parent collection, sharing state, per-request rollups, and
# ``legacy_query`` — Metabase's legacy-MBQL rendering of the query, which fully duplicates
# the (already-legacy) ``dataset_query`` we fetch, so it only bloats the file.
_CARD_STRIP_KEYS = frozenset(
    {
        "view_count",
        "last_used_at",
        "cache_invalidated_at",
        "metabase_version",
        "legacy_query",
        "collection",
        "made_public_by_id",
        "public_uuid",
        "initially_published_at",
        "archived_directly",
        "card_schema",
        "collection_preview",
        "moderation_reviews",
        "average_query_time",
        "last_query_start",
        "dashboard_count",
        "parameter_usage_count",
        "param_fields",
    }
)

# Dashboard equivalents of the same runtime churn.
_DASHBOARD_STRIP_KEYS = frozenset(
    {
        "view_count",
        "last_viewed_at",
        "last_used_param_values",
        "cache_invalidated_at",
        "collection",
        "collection_authority_level",
        "param_fields",
        "param_values",
        "made_public_by_id",
        "public_uuid",
        "moderation_reviews",
        "archived_directly",
    }
)

# Per-dashcard churn: the full embedded card blob (dumped in its own file, referenced
# here by ``card_id``) and the dashcard's own timestamps.
_DASHCARD_STRIP_KEYS = frozenset({"card", "created_at", "updated_at"})

# The Metabase UI serves a saved question at ``/question/<id>`` (the API model is
# ``card``); dashboards and collections keep their names.
_URL_KIND_PATHS = {
    "card": "question",
    "dashboard": "dashboard",
    "collection": "collection",
}


# Cap the slug so the on-disk filename (``<id>-<slug>.json``, with the id prefix and suffix
# riding on top) stays well under ~143 bytes — the practical filename limit on encrypted
# filesystems such as eCryptfs (far below ext4's 255). Otherwise an object with an absurdly
# long name produces a filename that overflows the limit and crashes the write.
_MAX_SLUG_BYTES = 120


def slugify(name: str | None) -> str:
    """Turn an object name into one safe, readable path segment.

    The id already carries identity; the slug only makes the tree human-scannable, so a
    stable lowercase form is enough. Unicode *letters* are kept (readable, and modern
    filesystems handle them), but every non-word character — punctuation, whitespace, path
    separators, control chars — folds to a single hyphen so the name stays portable across
    filesystems (no ``:`` ``?`` ``%`` ``[`` ``]`` …) and safe to shell-glob. Over-long slugs
    are truncated on a UTF-8 boundary; the ``<id>-`` prefix still keeps the filename unique.
    """
    # ``\w`` is unicode-aware: it keeps letters, digits and underscore; every run of anything
    # else becomes one hyphen. A second pass collapses hyphens left adjacent to kept ones.
    text = re.sub(r"[^\w-]+", "-", name or "")
    text = re.sub(r"-+", "-", text)
    slug = text.strip("-").lower()
    if len(slug.encode("utf-8")) > _MAX_SLUG_BYTES:
        # Cut at the byte budget, drop any partial trailing char, then any trailing hyphen.
        slug = slug.encode("utf-8")[:_MAX_SLUG_BYTES].decode("utf-8", errors="ignore").rstrip("-")
    return slug or "unnamed"


def object_filename(obj: dict[str, Any]) -> str:
    """Return the ``<id>-<slug>`` basename used for an object's file(s)."""
    return f"{obj['id']}-{slugify(obj.get('name'))}"


def object_url(base_url: str, kind: str, obj_id: int) -> str:
    """Build the live-instance URL for an object so a snapshot stays actionable.

    ``kind`` is the API model name (``card`` / ``dashboard`` / ``collection``); the
    card→``/question/`` UI-route quirk is handled internally.
    """
    return f"{base_url.rstrip('/')}/{_URL_KIND_PATHS[kind]}/{obj_id}"


def collection_dir_parts(collection: dict[str, Any], by_id: dict[int, dict[str, Any]]) -> list[str]:
    """Return the nested directory names that place ``collection`` in the tree.

    A collection's ``location`` is an ancestor-id path like ``/1016/42/`` (root is
    ``/``). Each ancestor id is mapped through ``by_id`` to a ``<id>-<slug>`` segment in
    root-to-leaf order, then the collection's own segment is appended. Ancestors missing
    from ``by_id`` degrade to an ``<id>-unnamed`` segment rather than failing.
    """
    location = collection.get("location") or "/"
    parts: list[str] = []
    for token in location.strip("/").split("/"):
        if not token:
            continue
        ancestor_id = int(token)
        ancestor = by_id.get(ancestor_id)
        name = ancestor.get("name") if ancestor else None
        parts.append(f"{ancestor_id}-{slugify(name)}")
    parts.append(object_filename(collection))
    return parts


def _strip(obj: dict[str, Any], keys: frozenset[str]) -> None:
    """Remove ``keys`` from ``obj`` in place; keys may be absent."""
    for key in keys:
        obj.pop(key, None)


def _strip_can_keys(obj: dict[str, Any]) -> None:
    """Remove all ``can_*`` permission flags, which vary per request/user."""
    for key in [k for k in obj if k.startswith("can_")]:
        del obj[key]


def canonicalize_card(card: dict[str, Any], base_url: str) -> dict[str, Any]:
    """Canonicalize a card (question or model) for deterministic dumping.

    Deep-copies so the caller's dict is untouched, drops the runtime-churn strip-set and
    ``can_*`` flags, normalizes ``result_metadata`` (drop per-column ``fingerprint``, a
    sampled statistic that drifts on its own) and the embedded ``creator`` (drop
    ``last_login``), replaces a native query's inline SQL with a pointer to its sibling
    ``.sql`` file (see below), and adds the actionable ``url``.
    """
    result = copy.deepcopy(card)
    _strip(result, _CARD_STRIP_KEYS)
    _strip_can_keys(result)

    result_metadata = result.get("result_metadata")
    if isinstance(result_metadata, list):
        for column in result_metadata:
            if isinstance(column, dict):
                column.pop("fingerprint", None)

    creator = result.get("creator")
    if isinstance(creator, dict):
        creator.pop("last_login", None)

    # A native query's SQL would be an unreadable one-line escaped blob inside the JSON.
    # The command writes the real SQL to a sibling ``<id>-<slug>.sql`` file, so replace the
    # inline value with a relative pointer to it. MBQL (structured) queries stay inline —
    # they are already readable JSON.
    dataset_query = result.get("dataset_query")
    if isinstance(dataset_query, dict) and dataset_query.get("type") == "native":
        native = dataset_query.get("native")
        if isinstance(native, dict) and isinstance(native.get("query"), str):
            native["query"] = f"./{object_filename(result)}.sql"

    result["url"] = object_url(base_url, "card", result["id"])
    return result


def canonicalize_dashboard(dash: dict[str, Any], base_url: str) -> dict[str, Any]:
    """Canonicalize a dashboard for deterministic dumping.

    Deep-copies, drops the runtime-churn strip-set and ``can_*`` flags, normalizes the
    embedded ``creator`` (drop ``last_login``), and walks ``dashcards`` dropping each
    embedded ``card`` blob (kept only by ``card_id`` — the card is dumped in its own
    file) plus the dashcard's own timestamps. Adds the actionable ``url``.
    """
    result = copy.deepcopy(dash)
    _strip(result, _DASHBOARD_STRIP_KEYS)
    _strip_can_keys(result)

    creator = result.get("creator")
    if isinstance(creator, dict):
        creator.pop("last_login", None)

    dashcards = result.get("dashcards")
    if isinstance(dashcards, list):
        for dashcard in dashcards:
            if isinstance(dashcard, dict):
                _strip(dashcard, _DASHCARD_STRIP_KEYS)

    result["url"] = object_url(base_url, "dashboard", result["id"])
    return result


def canonicalize_collection(coll: dict[str, Any], base_url: str) -> dict[str, Any]:
    """Canonicalize a collection's own metadata for its ``_collection.json``.

    Deep-copies, drops ``children`` (the tree nesting from ``/collection/tree`` — the
    hierarchy is represented by the directory layout, not repeated inside every node)
    and ``can_*`` permission flags, and adds the actionable ``url``.
    """
    result = copy.deepcopy(coll)
    result.pop("children", None)
    _strip_can_keys(result)
    result["url"] = object_url(base_url, "collection", result["id"])
    return result


def extract_native_sql(card: dict[str, Any]) -> str | None:
    """Return the native SQL for a native card (newlines normalized to LF), else ``None``.

    Requires the legacy MBQL shape (``cards.get(id, legacy_mbql=True)``): native cards
    carry ``dataset_query = {type: "native", native: {query, ...}, ...}``; MBQL cards use
    ``type: "query"`` and have no SQL to extract. Metabase sometimes returns CRLF line
    endings; normalizing to LF keeps the ``.sql`` files clean on disk and their diffs stable
    regardless of the source's or git's line-ending handling.
    """
    dataset_query = card.get("dataset_query")
    if not isinstance(dataset_query, dict) or dataset_query.get("type") != "native":
        return None
    native = dataset_query.get("native")
    if not isinstance(native, dict):
        return None
    query = native.get("query")
    if not isinstance(query, str):
        return None
    return query.replace("\r\n", "\n").replace("\r", "\n")


def dumps_canonical(obj: Any) -> str:
    """Serialize ``obj`` deterministically: sorted keys, indented, trailing newline.

    ``ensure_ascii=False`` keeps unicode readable; ``sort_keys`` plus the newline make
    the output stable across runs and friendly to line-based diffs.
    """
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
