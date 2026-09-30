from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from sampletones_tools.tracker_playback.commands.face import TargetFace

if TYPE_CHECKING:
    from sampletones_tools.tracker_playback.targets.protocol import PlaybackTarget

NAME: Final[str] = "bitphase"
HELP: Final[str] = "export each project to a Bitphase document (.btp) and play it with a Bitphase checkout's own engine"
CHECKOUT_HELP: Final[str] = "the Bitphase source checkout whose engine plays the documents, with its packages installed"


@dataclass(frozen=True)
class BitphaseArguments:
    """What the Bitphase target is given: the checkout whose engine plays the documents."""

    checkout: Path


def configure(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--checkout",
        type=Path,
        required=True,
        help=CHECKOUT_HELP,
    )


def locate(arguments: Namespace) -> PlaybackTarget:
    """The Bitphase target playing documents with the checkout the options name.

    Raises:
        EngineError: If node is absent, or the checkout lacks a file the trace loads.
    """
    given = BitphaseArguments(checkout=arguments.checkout)

    from sampletones_tools.tracker_playback.targets.bitphase.target import BitphaseTarget

    return BitphaseTarget.located(given.checkout)


BITPHASE: Final[TargetFace] = TargetFace(
    name=NAME,
    help=HELP,
    configure=configure,
    locate=locate,
)
