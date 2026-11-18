import math
from dataclasses import dataclass
from typing import Final, List, Tuple

from assets.footage.specification import Listening, Timeline

FRAME_PRECISION: Final[int] = 9


class FrameRateError(ValueError):
    """Raised when footage is filmed at a frame rate the document's tick rate holds no whole number of."""


@dataclass(frozen=True)
class Run:
    """Frames of the footage, from ``first`` up to ``last`` exclusive, filmed under one listening."""

    listening: Listening
    first: int
    last: int


@dataclass(frozen=True)
class Schedule:
    """The footage laid on the document's tick grid: frame ``i`` shows the playhead at tick
    ``first_tick + i * ticks_per_frame``, the instant the reconstruction's instructions change.

    Every cut between two listenings falls on a frame, so the picture and the soundtrack change together.
    """

    first_tick: int
    ticks_per_frame: int
    frame_count: int
    runs: Tuple[Run, ...]

    def tick(self, frame: int) -> int:
        """The tick frame ``frame`` shows the playhead at."""
        return self.first_tick + frame * self.ticks_per_frame

    def listening(self, frame: int) -> Listening:
        """The listening frame ``frame`` is filmed under."""
        return next(run.listening for run in self.runs if run.first <= frame < run.last)


def schedule(timeline: Timeline, *, tick_rate: int, frame_rate: int) -> Schedule:
    """Lays ``timeline`` on a grid of ``tick_rate`` ticks a second, filmed at ``frame_rate`` frames a second.

    The footage opens on the tick nearest its start, and a listening takes over from the first frame at or
    after the moment its segment begins.

    Raises:
        FrameRateError: If ``tick_rate`` is no whole multiple of ``frame_rate``.
    """
    if tick_rate % frame_rate:
        raise FrameRateError(f"A tick rate of {tick_rate} Hz holds no whole number of frames at {frame_rate} fps")

    ticks_per_frame = tick_rate // frame_rate
    first_tick = round(timeline.start * tick_rate)
    opening = first_tick / tick_rate
    frame_count = math.floor((timeline.end - opening) * frame_rate)
    firsts = [
        max(0, math.ceil(round((segment.start - opening) * frame_rate, FRAME_PRECISION)))
        for segment in timeline.segments
    ]
    runs: List[Run] = []
    for segment, first, last in zip(timeline.segments, firsts, [*firsts[1:], frame_count]):
        if first < last:
            runs.append(Run(listening=segment.listening, first=first, last=last))

    return Schedule(first_tick=first_tick, ticks_per_frame=ticks_per_frame, frame_count=frame_count, runs=tuple(runs))
