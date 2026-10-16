from dataclasses import dataclass, field
from typing import Callable, Dict, Generic, List, Optional

from sampletones_core.audio.output import Ending, Playback
from sampletones_core.audio.output.source import ReportT


@dataclass
class Heard(Generic[ReportT]):
    """What an owner heard of one playback, in the order it landed.

    Attributes:
        positions: Every position delivered.
        endings: Every end report delivered.
        ends_after_positions: Whether every position landed before the first end report.
        streams_open_at_end: Whether the device held a stream open as the end report landed.
    """

    positions: List[ReportT] = field(default_factory=list)
    endings: List[Ending] = field(default_factory=list)
    ends_after_positions: bool = True
    streams_open_at_end: Optional[bool] = None


class RecordingListener(Generic[ReportT]):
    """An owner keeping what it hears of every playback it started, each one apart from the others."""

    def __init__(self, *, streams_open: Callable[[], bool]) -> None:
        self._streams_open = streams_open
        self._heard: Dict[Playback[ReportT], Heard[ReportT]] = {}

    def heard(self, playback: Playback[ReportT]) -> Heard[ReportT]:
        return self._heard.setdefault(playback, Heard())

    def positioned(self, playback: Playback[ReportT], report: ReportT) -> None:
        heard = self.heard(playback)
        if heard.endings:
            heard.ends_after_positions = False

        heard.positions.append(report)

    def ended(self, playback: Playback[ReportT], ending: Ending) -> None:
        heard = self.heard(playback)
        heard.endings.append(ending)
        heard.streams_open_at_end = self._streams_open()
