from argparse import ArgumentParser, Namespace
from typing import Final

from sampletones_shared.command import Command

NAME: Final[str] = "shortcut-actions"
HELP: Final[str] = "hold every action to its keys, its name and the call it makes"


def configure(parser: ArgumentParser) -> None:
    del parser


def run(arguments: Namespace) -> int:
    """Reports every action left short of a combination, a name, or the call it makes."""
    del arguments

    from sampletones_tools.checks.shortcut_actions import check, report

    return report(check())


SHORTCUT_ACTIONS: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
