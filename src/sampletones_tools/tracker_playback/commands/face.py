from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sampletones_tools.tracker_playback.targets.protocol import PlaybackTarget


@dataclass(frozen=True)
class TargetFace:
    """The command-line face of one playback target: its name, its help, its options and how it is found.

    Listing the commands reads every face, so a face states its target's options and reaches the target
    itself once a check runs.

    Attributes:
        name: The target's name, as the command line spells it.
        help: One line saying what the target exports to and what plays it.
        configure: Adds the options the target needs, such as where its tracker lives.
        locate: Builds the target from the parsed options, once its tracker is found.
    """

    name: str
    help: str
    configure: Callable[[ArgumentParser], None]
    locate: Callable[[Namespace], PlaybackTarget]
