from dataclasses import dataclass
from fractions import Fraction
from typing import List, Tuple

from sampletones_core.timing.distribution import nearest, split_by_halving
from sampletones_core.timing.meter import Meter
from sampletones_core.timing.rate import RowRate


@dataclass(frozen=True)
class Groove:
    """The engine ticks each row of a pattern lasts.

    An engine that takes one speed value per row reaches a fractional row rate by varying
    that value from row to row, which is how a tempo its speed column alone cannot state
    still comes out right on average. Every bar starts on the tick nearest its exact start,
    and inside a bar the meter places the longer rows on the strongest positions first.

    Attributes:
        ticks: One tick count per pattern row, in order.
    """

    ticks: Tuple[int, ...]

    @property
    def total_ticks(self) -> int:
        """How many engine ticks the whole pattern lasts."""
        return sum(self.ticks)

    @property
    def mean_ticks_per_row(self) -> Fraction:
        """The row rate the groove realizes, which states what a bounded groove reached."""
        return Fraction(self.total_ticks, len(self.ticks))

    @property
    def is_uniform(self) -> bool:
        """Whether every row lasts alike, so a single speed value carries the tempo."""
        return len(set(self.ticks)) == 1

    def ticks_across(self, row_index: int, rows: int) -> int:
        """How many engine ticks pass over ``rows`` rows starting at ``row_index``.

        Every frame of an order plays one whole pattern, so a span running past the pattern's last
        row goes on from the first row of the next one.

        Args:
            row_index: The row the span starts on, within the pattern.
            rows: How many rows the span covers, at least zero.

        Returns:
            int: The ticks those rows last.
        """
        length = len(self.ticks)
        patterns, remainder = divmod(rows, length)
        opening = sum(self.ticks[(row_index + offset) % length] for offset in range(remainder))
        return patterns * self.total_ticks + opening


def calculate_groove(
    rate: RowRate,
    meter: Meter,
    *,
    minimum_ticks: int,
    maximum_ticks: int,
) -> Groove:
    """Builds the per-row tick counts that carry a row rate across one pattern.

    Each bar starts on the tick nearest its exact start, counted from the pattern's first row, so
    the pattern lasts the whole number of ticks nearest its exact length and no bar strays half a
    tick from where the tempo puts it. A bar's ticks are then halved down its beats and rows by
    :func:`~sampletones_core.timing.distribution.split_by_halving`, which settles the surplus on
    the strongest positions.

    The rate is first held within the engine's range, so a tempo asking for rows shorter than the
    shortest the engine plays sounds every row at that shortest length.

    Args:
        rate: The exact ticks one row lasts.
        meter: The pattern's length and its beat and bar grouping.
        minimum_ticks: The fewest ticks the engine holds a row for.
        maximum_ticks: The most ticks the engine holds a row for.

    Returns:
        Groove: One tick count per row of the pattern.
    """
    row_ticks = rate.bounded(
        minimum_ticks=minimum_ticks,
        maximum_ticks=maximum_ticks,
    ).ticks_per_row
    ticks: List[int] = []
    bar_start = 0
    for beats in meter.spans:
        bar_end = bar_start + sum(beats)
        bar_ticks = _bar_line(bar_end, row_ticks) - _bar_line(bar_start, row_ticks)
        ticks.extend(split_by_halving(bar_ticks, beats, row_ticks=row_ticks))
        bar_start = bar_end

    return Groove(ticks=tuple(ticks))


def _bar_line(row: int, row_ticks: Fraction) -> int:
    """The tick a bar starting on ``row`` starts on: the one nearest its exact start."""
    return nearest(row * row_ticks)
