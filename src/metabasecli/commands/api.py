"""Raw Metabase API passthrough command.

Sends an arbitrary HTTP request to the Metabase API and prints the server's
response verbatim, modeled on ``glab api`` / ``gh api``. It is an escape hatch
for endpoints without a dedicated command and the primary tool for verifying
API behavior across Metabase versions.
"""

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from ..context import get_context
from ..logging import console, error_console
from ..output import handle_api_error

_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _normalize_endpoint(endpoint: str) -> str:
    """Normalize an endpoint to a path relative to ``{url}/api``.

    Accepts ``/card/1``, ``card/1``, and ``/api/card/1`` as equivalent. Any
    inline query string is preserved and rides along to httpx untouched.
    """
    path = endpoint.strip()
    if path.startswith("/api/"):
        path = path[len("/api") :]
    elif path.startswith("api/"):
        path = path[len("api") :]
    if not path.startswith("/"):
        path = "/" + path
    return path


def _read_body(input_ref: str) -> str:
    """Read a request body from a file path, or from stdin when ``-``."""
    if input_ref == "-":
        return typer.get_text_stream("stdin").read()
    return Path(input_ref).read_text()


def _print_response_body(text: str) -> None:
    """Print the response body: pretty JSON when parseable, verbatim otherwise."""
    if not text:
        return
    try:
        console.print_json(text)
    except ValueError:
        console.print(text, markup=False, highlight=False)


def api_command(
    endpoint: Annotated[
        str,
        typer.Argument(help='API endpoint, e.g. /card/1 or "/search?q=x". A leading /api is optional.'),
    ],
    method: Annotated[
        str | None,
        typer.Option(
            "--method",
            "-X",
            help="HTTP method (GET, POST, PUT, PATCH, DELETE). Defaults to GET, or POST when --input is given.",
        ),
    ] = None,
    input_ref: Annotated[
        str | None,
        typer.Option("--input", help="Read a JSON request body from FILE, or - for stdin."),
    ] = None,
) -> None:
    """Send a raw request to the Metabase API and print the response.

    The response body is printed to stdout (pretty-printed when it is JSON) with
    no success/data envelope. On a non-2xx status the body is still printed, an
    "HTTP <status>" note is written to stderr, and the exit code is 1.

    Examples:
        metabase api /user/current
        metabase api "/search?q=revenue&models=dashboard"
        metabase api /card -X POST --input card.json
        cat card.json | metabase api /card --input -
    """
    ctx = get_context()

    resolved_method = (method or ("POST" if input_ref is not None else "GET")).upper()
    if resolved_method not in _ALLOWED_METHODS:
        allowed = ", ".join(sorted(_ALLOWED_METHODS))
        error_console.print(f"[red]Unsupported method '{resolved_method}'. Use one of: {allowed}.[/red]")
        raise typer.Exit(1)

    json_body: Any = None
    if input_ref is not None:
        raw = _read_body(input_ref)
        try:
            json_body = json.loads(raw)
        except json.JSONDecodeError as e:
            error_console.print(f"[red]Invalid JSON in request body: {e}[/red]")
            raise typer.Exit(1) from None

    path = _normalize_endpoint(endpoint)

    try:
        client = ctx.require_auth()
        response = client.request_raw(resolved_method, path, json_body=json_body)
    except Exception as e:
        handle_api_error(e, json_output=False, entity_name="API")
        raise typer.Exit(1) from None

    _print_response_body(response.text)

    if not response.is_success:
        error_console.print(f"[red]HTTP {response.status_code}[/red]")
        raise typer.Exit(1)
