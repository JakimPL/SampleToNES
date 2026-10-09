from dataclasses import dataclass
from fractions import Fraction
from functools import cached_property
from typing import Dict, Self, Tuple

from sampletones_core.project import Project
from sampletones_core.timing.bounds import TickBounds
from sampletones_core.timing.groove import Groove, bar_line, plan_bar
from sampletones_core.timing.meter import Meter
from sampletones_core.timing.rate import RowRate


@dataclass(frozen=True)
class BarSlot:
    """One bar of a pattern: the row it starts on and the row count of each of its beats.

    Attributes:
        first_row: The pattern row the bar starts on.
        beats: The row count of each of the bar's beats, in order.
    """

    first_row: int
    beats: Tuple[int, ...]

    @property
    def rows(self) -> int:
        """How many rows the bar spans."""
        return sum(self.beats)


@dataclass(frozen=True)
class SongTiming:
    """How many engine ticks every row of a song lasts, wherever the order plays it.

    Every bar starts on the tick nearest its exact start, counted from the song's first row, so
    the rounding never adds up and the song keeps its tempo however long it plays. Inside a bar,
    the bar's ticks are halved down its beats and rows, so the surplus settles on the strongest
    positions. The meter restarts at every pattern, as a tracker's highlights do, so every order
    frame starts a bar. Where the bar lines fall depends on how far into the song a frame plays,
    so two frames can differ by a tick in a bar.

    Each answer follows from the row's place alone. A player reaching a row, a seek and an export
    asking where a frame starts all read it directly. Once the exact lengths of a run of patterns add
    up to whole ticks, every frame after it plays the groove of the frame that many before, so each
    groove is planned once and kept.

    Attributes:
        rate: The exact ticks one row lasts under the project's tempo, speed and tick rate.
        meter: The pattern length and the beat and bar grouping the ticks are spread over.
        bounds: The shortest and the longest the player holds a row for.
    """

    rate: RowRate
    meter: Meter
    bounds: TickBounds

    @classmethod
    def from_project(cls, project: Project, *, bounds: TickBounds) -> Self:
        """Reads the timing a project plays at, taking the pattern length from its song.

        Args:
            project: The project whose settings and song set the timing.
            bounds: The shortest and the longest the player holds a row for.

        Returns:
            Self: The project's timing.
        """
        return cls(
            rate=RowRate.from_settings(project.settings),
            meter=Meter.from_settings(
                project.settings,
                rows=project.song.rows_per_pattern,
            ),
            bounds=bounds,
        )

    @cached_property
    def exact_row_ticks(self) -> Fraction:
        """The exact ticks one row lasts, held within what the player plays.

        A tempo asking for rows shorter than the shortest the player holds plays every row at that
        shortest length, so the song runs slower than its tempo states.
        """
        return self.rate.bounded(
            minimum_ticks=self.bounds.minimum,
            maximum_ticks=self.bounds.maximum,
        ).ticks_per_row

    @cached_property
    def bars(self) -> Tuple[BarSlot, ...]:
        """Every bar of a pattern, in order."""
        slots = []
        first_row = 0
        for beats in self.meter.spans:
            slots.append(BarSlot(first_row=first_row, beats=beats))
            first_row += sum(beats)

        return tuple(slots)

    @cached_property
    def period(self) -> int:
        """How many frames pass before the grooves repeat: the patterns whose exact lengths add up to whole ticks."""
        return (self.exact_row_ticks * self.meter.rows).denominator

    @cached_property
    def planned(self) -> Dict[int, Groove]:
        """The grooves planned so far, by their frame's place within the period."""
        return {}

    def groove(self, frame: int) -> Groove:
        """The ticks each row of the pattern lasts where order frame ``frame`` plays it.

        Args:
            frame: The order position, counted from 0.

        Returns:
            Groove: One tick count per pattern row.
        """
        phase = frame % self.period
        groove = self.planned.get(phase)
        if groove is None:
            groove = Groove(ticks=tuple(ticks for bar in self.bars for ticks in self._bar_plan(phase, bar)))
            self.planned[phase] = groove

        return groove

    def row_ticks(self, frame: int, row: int) -> int:
        """The ticks one row lasts where order frame ``frame`` plays it.

        Args:
            frame: The order position, counted from 0.
            row: The row within the pattern.

        Returns:
            int: The ticks the row lasts.
        """
        return self.groove(frame).ticks[row]

    def frame_tick(self, frame: int) -> int:
        """The engine tick order frame ``frame`` starts on.

        A frame starts a bar, so it starts on the tick nearest its exact start. The frame one past
        the order's last is where the song ends, so its tick is the length of the whole song: the
        whole number of ticks nearest its exact length.

        Args:
            frame: The order position, counted from 0.

        Returns:
            int: The ticks the order plays before ``frame`` begins.
        """
        return bar_line(frame * self.meter.rows, self.exact_row_ticks)

    def tick_at(self, frame: int, row: int) -> int:
        """The engine tick a row starts on, counted from the song's first tick.

        Args:
            frame: The order position, counted from 0.
            row: The row within the pattern.

        Returns:
            int: The ticks the song plays before the row begins.
        """
        return self.frame_tick(frame) + sum(self.groove(frame).ticks[:row])

    def ticks_across(
        self,
        frame: int,
        row: int,
        rows: int,
        *,
        frames: int,
    ) -> int:
        """How many engine ticks pass over ``rows`` rows starting at a row of the song.

        The order plays its frames in turn and returns to the first after the last, and every pass
        through it plays alike, so a span running past the song's end goes on from its start.

        Args:
            frame: The order position the span starts in.
            row: The row within that frame's pattern the span starts on.
            rows: How many rows the span covers, at least zero.
            frames: How many frames the order plays before it returns to the first.

        Returns:
            int: The ticks those rows last.
        """
        pattern_rows = self.meter.rows
        passes, remainder = divmod(frame * pattern_rows + row + rows, frames * pattern_rows)
        end_frame, end_row = divmod(remainder, pattern_rows)
        end = passes * self.frame_tick(frames) + self.tick_at(end_frame, end_row)
        return end - self.tick_at(frame, row)

    def _bar_plan(self, frame: int, bar: BarSlot) -> Tuple[int, ...]:
        start = frame * self.meter.rows + bar.first_row
        total = bar_line(start + bar.rows, self.exact_row_ticks) - bar_line(start, self.exact_row_ticks)
        return plan_bar(total, bar.beats, self.exact_row_ticks)
