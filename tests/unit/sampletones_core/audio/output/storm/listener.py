import threading
from dataclasses import dataclass
from typing import List

from sampletones_core.audio.output import Ending, Playback
from tests.suite.audio.timeline import Timeline

from .source import StormMark, StormSound


@dataclass(frozen=True)
class LandedMark:
    """A position as it landed on the owner's thread.

    Attributes:
        mark: The position.
        index: The events the device's timeline held as it landed.
        sought: The last seek the owner made before it landed.
        after_end: Whether the playback's end report had landed before it.
    """

    mark: StormMark
    index: int
    sought: int
    after_end: bool


@dataclass(frozen=True)
class LandedEnd:
    """An end report as it landed on the owner's thread.

    Attributes:
        ending: The report.
        index: The events the device's timeline held as it landed.
        engaged: Whether the playback still held the output as it landed.
    """

    ending: Ending
    index: int
    engaged: bool


class StormListener:
    """The owner of one storm playback, keeping each report as it landed and how far the device had come."""

    def __init__(self, sound: StormSound, timeline: Timeline) -> None:
        self.sound = sound
        self._timeline = timeline
        self._lock = threading.Lock()
        self._sought: int = 0
        self._marks: List[LandedMark] = []
        self._endings: List[LandedEnd] = []

    @property
    def marks(self) -> List[LandedMark]:
        with self._lock:
            return list(self._marks)

    @property
    def endings(self) -> List[LandedEnd]:
        with self._lock:
            return list(self._endings)

    def sought(self, position: int) -> None:
        """Keeps a seek the output accepted, from which every position landing later reads."""
        with self._lock:
            self._sought = position

    def positioned(self, playback: Playback[StormMark], report: StormMark) -> None:
        index = self._timeline.count()
        with self._lock:
            self._marks.append(LandedMark(mark=report, index=index, sought=self._sought, after_end=bool(self._endings)))

    def ended(self, playback: Playback[StormMark], ending: Ending) -> None:
        index = self._timeline.count()
        engaged = playback.engaged
        with self._lock:
            self._endings.append(LandedEnd(ending=ending, index=index, engaged=engaged))
