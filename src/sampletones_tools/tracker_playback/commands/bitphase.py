from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from sampletones_tools.tracker_playback.commands.face import TargetFace

if TYPE_CHECKING:
    from sampletones_tools.tracker_playback.targets.protocol import PlaybackTarget

NAME: Final[str] = "bitphase"
HELP: Final[str] = (
    "export each project to a Bitphase document (.btp) and play it with the engine of Bitphase's source code"
)
DIRECTORY_HELP: Final[str] = (
    "the directory holding Bitphase's source code, its packages installed, whose engine plays the documents"
)


@dataclass(frozen=True)
class BitphaseArguments:
    """What the Bitphase target is given: the directory of the source code whose engine plays the documents."""

    directory: Path


def configure(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--directory",
        type=Path,
        required=True,
        help=DIRECTORY_HELP,
    )


def locate(arguments: Namespace) -> PlaybackTarget:
    """The Bitphase target playing documents with the source code in the directory the options name.

    Raises:
        EngineError: If node is absent, or the directory lacks a file the trace loads.
    """
    given = BitphaseArguments(directory=arguments.directory)

    from sampletones_tools.tracker_playback.targets.bitphase.target import BitphaseTarget

    return BitphaseTarget.located(given.directory)


BITPHASE: Final[TargetFace] = TargetFace(
    name=NAME,
    help=HELP,
    configure=configure,
    locate=locate,
)
