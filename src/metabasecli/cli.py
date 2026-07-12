import sys
from typing import Annotated

import typer

from . import __version__
from .commands import (
    api_command,
    auth_app,
    cards_app,
    collections_app,
    dashboards_app,
    databases_app,
    resolve_command,
    search_command,
)
from .context import get_context
from .logging import error_console, setup_logging

app = typer.Typer(
    name="metabase",
    help="A command-line interface for Metabase.",
    no_args_is_help=True,
    rich_markup_mode=None,
)

# Register command groups
app.add_typer(auth_app, name="auth")
app.add_typer(databases_app, name="databases")
app.add_typer(collections_app, name="collections")
app.add_typer(cards_app, name="cards")
app.add_typer(dashboards_app, name="dashboards")

# Register aliases for cards
app.add_typer(cards_app, name="queries", hidden=True)
app.add_typer(cards_app, name="questions", hidden=True)

# Register standalone commands
app.command("search")(search_command)
app.command("resolve")(resolve_command)
app.command("api")(api_command)

_ctx = get_context()


def version_callback(value: bool) -> None:
    if value:
        print(f"metabase {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output.", is_eager=True)] = False,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile name to use.")] = "default",
    version: Annotated[
        bool | None,
        typer.Option("--version", "-V", help="Show version and exit.", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """Metabase CLI - interact with Metabase from the command line."""
    setup_logging(verbose=verbose)
    _ctx.verbose = verbose
    _ctx.profile = profile


def _hoist_global_options(argv: list[str]) -> list[str]:
    """Move global options to before the first subcommand.

    Typer/Click requires group-level options to appear before subcommands.
    This function allows users to place --profile, --verbose, and
    --version anywhere in the command line.
    """
    # Options that take a value
    value_options = {"--profile", "-p"}
    # Boolean flags
    flag_options = {"--verbose", "-v", "--version", "-V"}

    hoisted: list[str] = []
    rest: list[str] = []

    i = 0
    while i < len(argv):
        arg = argv[i]

        # Handle --profile=value form
        if any(arg.startswith(f"{opt}=") for opt in value_options):
            hoisted.append(arg)
            i += 1
        # Handle --profile value form
        elif arg in value_options:
            hoisted.append(arg)
            if i + 1 < len(argv):
                i += 1
                hoisted.append(argv[i])
            i += 1
        # Handle boolean flags
        elif arg in flag_options:
            hoisted.append(arg)
            i += 1
        else:
            rest.append(arg)
            i += 1

    return hoisted + rest


def cli() -> None:
    try:
        sys.argv[1:] = _hoist_global_options(sys.argv[1:])
        app()
    except Exception as e:
        error_console.print(f"[red]Error: {e}[/red]")
        if _ctx.verbose:
            error_console.print_exception()
        sys.exit(1)
