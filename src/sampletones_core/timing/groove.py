from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from typing import Final, Tuple

from sampletones_core.timing.distribution import nearest, split_by_halving

BAR_PLAN_CACHE_SIZE: Final[int] = 4096


@dataclass(frozen=True)
class Groove:
    """The engine ticks each row of one pattern lasts, where an order frame plays it.

    An engine that takes one speed value per row reaches a fractional row rate by varying
    that value from row to row, which is how a tempo its speed column alone cannot state
    still comes out right on average. Every bar starts on the tick nearest its exact start,
    and inside a bar the meter places the longer rows on the strongest positions first.

    Attributes:
        ticks: One tick count per pattern row, in order.
    """

    ticks: Tuple[int, ...]


def bar_line(row: int, row_ticks: Fraction) -> int:
    """The tick a bar starting on ``row`` of the song starts on: the one nearest its exact start.

    Args:
        row: The row the bar starts on, counted from the song's first row.
        row_ticks: The exact ticks one row lasts.

    Returns:
        int: The tick, counted from the song's first.
    """
    return nearest(row * row_ticks)


@lru_cache(maxsize=BAR_PLAN_CACHE_SIZE)
def plan_bar(
    total: int,
    beats: Tuple[int, ...],
    row_ticks: Fraction,
) -> Tuple[int, ...]:
    """The ticks each row of a bar lasts, the bar's total halved down its beats and rows.

    A bar lasts one of two totals wherever it falls in a song, the floor or the ceiling of its exact
    length, so each bar of a pattern has at most two plans, and they are kept once computed.

    Args:
        total: The ticks the bar lasts.
        beats: The row count of each of the bar's beats.
        row_ticks: The exact ticks one row lasts.

    Returns:
        Tuple[int, ...]: One tick count per row of the bar.
    """
    return split_by_halving(total, beats, row_ticks=row_ticks)
