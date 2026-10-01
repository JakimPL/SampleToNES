from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from sampletones_tools.tracker_playback.commands.face import TargetFace

if TYPE_CHECKING:
    from sampletones_tools.tracker_playback.targets.protocol import PlaybackTarget

NAME: Final[str] = "famitracker"
HELP: Final[str] = (
    "export each project to a FamiTracker module (.ftm), have FamiTracker export it to an NSF, "
    "and play the NSF's own driver on an emulated 6502"
)
EXECUTABLE_HELP: Final[str] = "FamiTracker.exe, which Wine runs on Linux and macOS"


@dataclass(frozen=True)
class FamiTrackerArguments:
    """What the FamiTracker target is given: the program that exports the modules."""

    executable: Path


def configure(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--executable",
        type=Path,
        required=True,
        help=EXECUTABLE_HELP,
    )


def locate(arguments: Namespace) -> PlaybackTarget:
    """The FamiTracker target exporting with the program the options name.

    Raises:
        FamiTrackerError: If the program is no Windows program file, or Wine is absent where it is needed.
    """
    given = FamiTrackerArguments(executable=arguments.executable)

    from sampletones_tools.tracker_playback.targets.famitracker.target import FamiTrackerTarget

    return FamiTrackerTarget.located(given.executable)


FAMITRACKER: Final[TargetFace] = TargetFace(
    name=NAME,
    help=HELP,
    configure=configure,
    locate=locate,
)
