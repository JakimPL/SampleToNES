from dataclasses import dataclass
from fractions import Fraction
from math import floor
from typing import Final, List, Tuple

from sampletones_core.timing.distribution import (
    distribute_by_halving,
    distribute_proportionally,
)
from sampletones_core.timing.metre import Metre
from sampletones_core.timing.rate import RowRate

HALF: Final[Fraction] = Fraction(1, 2)


@dataclass(frozen=True)
class Groove:
    """The engine ticks each row of a pattern lasts.

    An engine that takes one speed value per row reaches a fractional row rate by varying
    that value from row to row, which is how a tempo its speed column alone cannot state
    still comes out right on average. The variation is placed by metre, so the longer rows
    land on the bar, then the beat, then the subdivisions inside a beat.

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


def _pattern_ticks(
    rate: RowRate,
    rows: int,
    *,
    minimum_ticks: int,
    maximum_ticks: int,
) -> int:
    """Rounds a pattern's exact tick count to the nearest integer within the engine's speed range.

    Rounding once, on the pattern, is what makes the pattern's duration the closest the
    engine reaches; the metre then decides which rows carry the difference. Bounding the
    pattern total rather than each row keeps every row inside the range as a consequence,
    since a proportional split yields only the floor and the ceiling of the average.

    Args:
        rate: The exact ticks one row lasts.
        rows: The pattern's row count.
        minimum_ticks: The fewest ticks the engine holds a row for.
        maximum_ticks: The most ticks the engine holds a row for.

    Returns:
        int: The tick count the pattern's rows share.
    """
    exact = rate.ticks_per_row * rows
    return min(
        max(floor(exact + HALF), rows * minimum_ticks),
        rows * maximum_ticks,
    )


def calculate_groove(
    rate: RowRate,
    metre: Metre,
    *,
    minimum_ticks: int,
    maximum_ticks: int,
) -> Groove:
    """Builds the per-row tick counts that carry a row rate across one pattern.

    The pattern's tick total is shared among its bars, each bar's among its beats, and
    each beat's among its rows by halving — one rule applied at three levels, so the
    surplus ticks settle on the strongest position each level offers.

    Args:
        rate: The exact ticks one row lasts.
        metre: The pattern's length and its beat and bar grouping.
        minimum_ticks: The fewest ticks the engine holds a row for.
        maximum_ticks: The most ticks the engine holds a row for.

    Returns:
        Groove: One tick count per row of the pattern.
    """
    total = _pattern_ticks(
        rate,
        metre.rows,
        minimum_ticks=minimum_ticks,
        maximum_ticks=maximum_ticks,
    )
    bars = metre.spans
    bar_lengths = tuple(sum(beats) for beats in bars)

    ticks: List[int] = []
    for beats, bar_ticks in zip(
        bars,
        distribute_proportionally(
            total,
            bar_lengths,
        ),
    ):
        for beat_rows, beat_ticks in zip(
            beats,
            distribute_proportionally(
                bar_ticks,
                beats,
            ),
        ):
            ticks.extend(distribute_by_halving(beat_ticks, beat_rows))

    return Groove(ticks=tuple(ticks))
