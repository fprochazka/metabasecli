import logging

from rich.console import Console
from rich.logging import RichHandler

console = Console()
error_console = Console(stderr=True)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=error_console,
                rich_tracebacks=True,
                show_time=verbose,
                show_path=verbose,
            )
        ],
    )

    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
