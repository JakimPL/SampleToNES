from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Tuple

from sampletones_shared.command import Command

NAME: Final[str] = "rendered-literals"
HELP: Final[str] = "hold every case to comparing values, never the text it rendered"
TESTS_HELP: Final[str] = "directory of cases to read, repeatable; without it, the repository's tests"


@dataclass(frozen=True)
class RenderedLiteralsArguments:
    """What a rendered literal check is given: the directories of cases."""

    roots: Tuple[Path, ...]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--tests", type=Path, action="append", dest="roots", default=[], help=TESTS_HELP)


def run(arguments: Namespace) -> int:
    """Reports every case comparing text it rendered with a literal it spelled out."""
    given = RenderedLiteralsArguments(roots=tuple(arguments.roots))

    from sampletones_tools.checks.rendered_literals import TEST_ROOTS, check_cases, report

    return report(check_cases(given.roots or TEST_ROOTS))


RENDERED_LITERALS: Final[Command] = Command(name=NAME, help=HELP, configure=configure, run=run)
