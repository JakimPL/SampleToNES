from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional, Tuple

from sampletones_shared.command import Command

NAME: Final[str] = "unused-tags"
HELP: Final[str] = "hold every declared tag fragment to a read somewhere in the repository"
TAGS_HELP: Final[str] = "package declaring the tag fragments; without it, the application's tags package"
REFERENCE_ROOT_HELP: Final[str] = "directory to count reads in, repeatable; without it, src, tests and scripts"


@dataclass(frozen=True)
class UnusedTagsArguments:
    """What an unused tag check is given: the tags package and the directories read for references."""

    tags: Optional[Path]
    reference_roots: Tuple[Path, ...]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--tags", type=Path, default=None, help=TAGS_HELP)
    parser.add_argument(
        "--reference-root",
        type=Path,
        action="append",
        dest="reference_roots",
        default=[],
        help=REFERENCE_ROOT_HELP,
    )


def run(arguments: Namespace) -> int:
    """Reports every tag fragment the repository declares and never reads."""
    given = UnusedTagsArguments(
        tags=arguments.tags,
        reference_roots=tuple(arguments.reference_roots),
    )

    from sampletones_tools.checks.unused_tags import (
        REFERENCE_ROOTS,
        TAGS_PACKAGE,
        check_reads,
        report,
    )

    unread = check_reads(
        given.tags if given.tags is not None else TAGS_PACKAGE,
        given.reference_roots or REFERENCE_ROOTS,
    )
    return report(unread)


UNUSED_TAGS: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
