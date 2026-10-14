from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, List, Optional

from sampletones_core.project.song_position import SongPosition

from .sound import Sound


class EndCause(Enum):
    """Why a playback ended, as its end report names it."""

    FINISHED = "finished"
    STOPPED = "stopped"
    TAKEN = "taken"
    FAILED = "failed"


@dataclass(frozen=True)
class Mark:
    """A position an owner drew, as the report landed.

    Attributes:
        position: The sample the mark stands at.
        written: The samples the device had received.
        ends_heard: The end reports the owner had heard before this one.
    """

    position: int
    written: int
    ends_heard: int


@dataclass(frozen=True)
class RowMark:
    """A row the song's playhead drew, with the samples the device had received when the report landed."""

    position: SongPosition
    written: int


@dataclass(frozen=True)
class End:
    """An end report an owner took, with the state the output stood in when it landed.

    Attributes:
        cause: The cause the report names.
        holding: Whether the owner still read itself engaged as the report landed.
        open_streams: The streams the device held open as the report landed.
    """

    cause: EndCause
    holding: bool
    open_streams: FrozenSet[int]


@dataclass(frozen=True)
class Told:
    """A failure told to a listener.

    Attributes:
        listener: The owner whose listener heard it, or ``None`` where the device's own error hook told
            the application.
        error: The failure.
    """

    listener: Optional[Sound]
    error: Exception


@dataclass(frozen=True)
class Wait:
    """A join the render thread made on an audio thread while a gesture ran."""

    joined: str


@dataclass
class OwnerLog:
    """What one owner heard, in the order it landed on the render thread."""

    marks: List[Mark] = field(default_factory=list)
    ends: List[End] = field(default_factory=list)
