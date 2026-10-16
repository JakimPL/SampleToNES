from dataclasses import dataclass
from typing import Union

from sampletones_core.audio.output import Ending
from sampletones_core.project.song_position import SongPosition


@dataclass(frozen=True)
class SongPositionUpdate:
    position: SongPosition


@dataclass(frozen=True)
class SongPlaybackEnded:
    """The song's one end report, naming why it ended, and the failure behind it where it failed."""

    ending: Ending


SongPlayerResult = Union[SongPositionUpdate, SongPlaybackEnded]
