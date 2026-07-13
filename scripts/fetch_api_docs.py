#!/usr/bin/env python3
"""Fetch version-scoped Metabase API docs into ``docs/api/<version>/``.

Everything is downloaded from GitHub over the public internet -- no running
Metabase instance and no authentication are required:

* Older Metabase (e.g. ``v1.48.2``) ships per-endpoint markdown under
  ``docs/api/`` in its source tree; those files are copied verbatim.
* Newer Metabase (``v0.60+``) ships a single committed OpenAPI spec at
  ``docs/api.json``; it is downloaded and grep-friendly per-tag markdown is
  generated from it.

Usage::

    uv run python scripts/fetch_api_docs.py [v48|v60|all]

To add a future version, add an entry to ``VERSIONS`` below.

Set ``GITHUB_TOKEN`` in the environment to lift the unauthenticated GitHub API
rate limit (only the directory listings hit the API; the file downloads go to
raw.githubusercontent.com and are not rate-limited the same way).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path

REPO = "metabase/metabase"

# version short name -> where its docs come from.
#   "markdown": copy the per-endpoint markdown under docs/api/ of the source tree.
#   "openapi":  download the committed docs/api.json and generate markdown from it.
VERSIONS: dict[str, dict[str, str]] = {
    "v48": {"tag": "v1.48.2", "source": "markdown"},
    "v60": {"tag": "v0.60.2", "source": "openapi"},
}

DOCS_API_DIR = Path(__file__).resolve().parent.parent / "docs" / "api"

# Canonical ordering so the generated files are stable across re-runs.
METHOD_ORDER = ["get", "post", "put", "patch", "delete", "head", "options"]


def _http_get(url: str, accept: str | None = None) -> bytes:
    """GET ``url`` and return the raw body, raising on any non-2xx response."""
    request = urllib.request.Request(url)
    request.add_header("User-Agent", "metabasecli-fetch-api-docs")
    if accept:
        request.add_header("Accept", accept)
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - fixed https hosts
        return response.read()


def _github_contents(path: str, ref: str) -> list[dict]:
    """List a directory in the repo at ``ref`` via the GitHub contents API."""
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={ref}"
    return json.loads(_http_get(url, accept="application/vnd.github+json"))


def _fetch_markdown_docs(tag: str, dest: Path) -> None:
    """Copy every ``*.md`` under the source tree's ``docs/api/`` (recursively)."""
    count = _copy_contents_dir("docs/api", tag, dest)
    print(f"  {count} markdown files")


def _copy_contents_dir(path: str, ref: str, dest: Path) -> int:
    count = 0
    for entry in sorted(_github_contents(path, ref), key=lambda e: e["name"]):
        if entry["type"] == "dir":
            subdest = dest / entry["name"]
            subdest.mkdir(parents=True, exist_ok=True)
            count += _copy_contents_dir(entry["path"], ref, subdest)
        elif entry["type"] == "file" and entry["name"].endswith(".md"):
            (dest / entry["name"]).write_bytes(_http_get(entry["download_url"]))
            count += 1
    return count


def _fetch_openapi_docs(tag: str, dest: Path, version: str) -> None:
    """Download the committed OpenAPI spec and generate per-tag markdown."""
    raw = _http_get(f"https://raw.githubusercontent.com/{REPO}/{tag}/docs/api.json")
    (dest / "openapi.json").write_bytes(raw)
    spec = json.loads(raw)
    count = _generate_markdown(spec, dest, tag, version)
    print(f"  openapi.json + {count} markdown files")


def _generate_markdown(spec: dict, dest: Path, tag: str, version: str) -> int:
    groups: dict[str, list[tuple[str, str, dict]]] = {}
    for path in sorted(spec.get("paths", {})):
        path_item = spec["paths"][path]
        for method in path_item:
            if method.lower() not in METHOD_ORDER:
                continue  # skip non-operation keys (parameters, summary, $ref, ...)
            operation = path_item[method]
            groups.setdefault(_group_key(operation, path), []).append((path, method.lower(), operation))

    for group in sorted(groups):
        operations = sorted(groups[group], key=lambda t: (t[0], METHOD_ORDER.index(t[1])))
        filename = _group_filename(group)
        (dest / filename).write_text(_render_group(group, operations, tag, version))
    return len(groups)


def _group_key(operation: dict, path: str) -> str:
    """The OpenAPI tag if present, else ``/api/<first-path-segment>``."""
    tags = operation.get("tags")
    if tags:
        return tags[0]
    segments = [segment for segment in path.split("/") if segment]
    if segments and segments[0] == "api":
        segments = segments[1:]
    return "/api/" + (segments[0] if segments else "misc")


def _group_filename(group: str) -> str:
    name = group.removeprefix("/api/").removeprefix("/").strip("/")
    return f"{name.replace('/', '-') or 'index'}.md"


def _render_group(group: str, operations: list[tuple[str, str, dict]], tag: str, version: str) -> str:
    lines = [
        f"# {group}",
        "",
        f"Metabase `{tag}` -- generated from `docs/api/{version}/openapi.json` "
        f"by `scripts/fetch_api_docs.py`. Do not edit by hand.",
        "",
    ]
    for path, method, operation in operations:
        lines.extend(_render_operation(path, method, operation))
    return "\n".join(lines).rstrip("\n") + "\n"


def _render_operation(path: str, method: str, operation: dict) -> list[str]:
    lines = [f"## {method.upper()} {path}", ""]

    summary = (operation.get("summary") or "").strip()
    # Metabase's summary is usually just "GET /api/card", which the heading already says.
    if summary and summary.upper() != f"{method} {path}".upper():
        lines += [summary, ""]

    description = (operation.get("description") or "").strip()
    if description:
        lines += [description, ""]

    parameters = operation.get("parameters") or []
    if parameters:
        lines += ["### Parameters", "", "| Name | In | Type | Required |", "| --- | --- | --- | --- |"]
        for parameter in parameters:
            name = parameter.get("name", "")
            location = parameter.get("in", "")
            type_str = _type_str(parameter.get("schema", {}))
            required = "yes" if parameter.get("required") else "no"
            lines.append(f"| `{name}` | {location} | {type_str} | {required} |")
        lines.append("")

    body = _request_body_properties(operation)
    if body:
        lines += ["### Request body", "", "| Name | Type | Required |", "| --- | --- | --- |"]
        for name, type_str, required in body:
            lines.append(f"| `{name}` | {type_str} | {required} |")
        lines.append("")

    return lines


def _request_body_properties(operation: dict) -> list[tuple[str, str, str]]:
    content = (operation.get("requestBody") or {}).get("content") or {}
    if not content:
        return []
    content_type = next(
        (ct for ct in ("application/json", "application/x-www-form-urlencoded") if ct in content),
        sorted(content)[0],
    )
    schema = content[content_type].get("schema") or {}
    properties = schema.get("properties")
    if not properties:
        return []
    required = set(schema.get("required") or [])
    return [(name, _type_str(properties[name]), "yes" if name in required else "no") for name in properties]


def _type_str(schema: dict) -> str:
    """Compact, human-readable type name for an OpenAPI schema fragment."""
    if not isinstance(schema, dict):
        return "any"
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    for combinator in ("oneOf", "anyOf", "allOf"):
        if combinator in schema:
            parts: list[str] = []
            for member in schema[combinator]:
                # flatten nested combinators so e.g. (object|null) | null collapses to object|null
                for piece in _type_str(member).split("|"):
                    if piece not in parts:
                        parts.append(piece)
            return "|".join(parts)
    type_ = schema.get("type")
    if type_ == "array":
        return f"array<{_type_str(schema.get('items', {}))}>"
    if isinstance(type_, list):
        return "|".join(type_)
    if type_:
        return type_
    if "enum" in schema:
        return "enum"
    return "object" if "properties" in schema else "any"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="fetch_api_docs.py",
        description=(
            "Fetch version-scoped Metabase API docs into docs/api/<version>/. "
            "Downloads from GitHub over the public internet; no Metabase instance or auth required."
        ),
    )
    parser.add_argument(
        "version",
        nargs="?",
        default="all",
        choices=[*VERSIONS, "all"],
        help="Which version set to fetch (default: all).",
    )
    args = parser.parse_args(argv[1:])

    targets = list(VERSIONS) if args.version == "all" else [args.version]
    for version in targets:
        entry = VERSIONS[version]
        dest = DOCS_API_DIR / version
        print(f"Fetching {version} ({entry['tag']}) -> {dest.relative_to(DOCS_API_DIR.parent.parent)}")
        if dest.exists():
            shutil.rmtree(dest)  # start clean so removed upstream files don't linger
        dest.mkdir(parents=True, exist_ok=True)
        if entry["source"] == "markdown":
            _fetch_markdown_docs(entry["tag"], dest)
        else:
            _fetch_openapi_docs(entry["tag"], dest, version)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
