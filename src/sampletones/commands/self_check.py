from argparse import ArgumentParser, Namespace
from typing import Final

from sampletones_shared.command import Command

NAME: Final[str] = "self-check"
HELP: Final[str] = "verify that this build's imports, bundled resources and configuration files are usable"


def configure(parser: ArgumentParser) -> None:
    del parser


def run(arguments: Namespace) -> int:
    """Runs every startup check and answers with the status a packaged build is held to."""
    del arguments

    from sampletones.self_check import run_self_check

    return run_self_check()


SELF_CHECK: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
