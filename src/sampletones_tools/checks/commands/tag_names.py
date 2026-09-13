from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Tuple

from sampletones_shared.command import Command

NAME: Final[str] = "tag-names"
HELP: Final[str] = "hold every tag constant's name to the tag it composes"
FILES_HELP: Final[str] = "modules to check"
ALL_HELP: Final[str] = "check every module of the tags package instead of named files"


@dataclass(frozen=True)
class TagNamesArguments:
    """What a tag name check is given: the modules, or the whole tags package."""

    files: Tuple[Path, ...]
    everything: bool


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("files", nargs="*", type=Path, help=FILES_HELP)
    parser.add_argument("--all", action="store_true", help=ALL_HELP)


def run(arguments: Namespace) -> int:
    """Reports any tag constant whose name departs from the tag it composes."""
    given = TagNamesArguments(files=tuple(arguments.files), everything=arguments.all)

    from sampletones_tools.checks.tag_names import check_tags, report

    return report(check_tags(given.files, given.everything))


TAG_NAMES: Final[Command] = Command(name=NAME, help=HELP, configure=configure, run=run)
