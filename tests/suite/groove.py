from fractions import Fraction
from itertools import accumulate
from math import ceil, floor
from typing import List, Sequence, Tuple

from sampletones_core.timing.meter import Meter


def bar_rows(meter: Meter, frames: int) -> Tuple[int, ...]:
    """The row every bar of ``frames`` patterns starts on, counted from the song's first row.

    The meter restarts at every pattern, so each pattern opens a bar.
    """
    starts: List[int] = []
    for frame in range(frames):
        row = frame * meter.rows
        for beats in meter.spans:
            starts.append(row)
            row += sum(beats)

    return tuple(starts)


def beat_spans(meter: Meter, frames: int) -> Tuple[Tuple[int, int], ...]:
    """The first row and the row count of every beat of ``frames`` patterns."""
    spans: List[Tuple[int, int]] = []
    for frame in range(frames):
        row = frame * meter.rows
        for beats in meter.spans:
            for beat in beats:
                spans.append((row, beat))
                row += beat

    return tuple(spans)


def bar_line_drift(
    ticks: Sequence[int],
    starts: Sequence[int],
    row_ticks: Fraction,
) -> Fraction:
    """The furthest a bar starts from its exact start, in ticks, over a run of rows.

    A row's exact start is its index times ``row_ticks``, counted from the run's first row, and its
    played start is the ticks every row before it lasted.

    Args:
        ticks: The ticks each row of the run lasts.
        starts: The row every bar starts on.
        row_ticks: The exact ticks one row lasts.

    Returns:
        Fraction: The largest gap between a bar's played start and its exact one.
    """
    played = (0, *accumulate(ticks))
    return max(abs(played[row] - row * row_ticks) for row in starts)


def is_proportional(ticks: Sequence[int], row_ticks: Fraction) -> bool:
    """Whether every row lasts the floor or the ceiling of its exact length."""
    return all(floor(row_ticks) <= row <= ceil(row_ticks) for row in ticks)


def surplus_rows(beat: Sequence[int], row_ticks: Fraction) -> Tuple[int, ...]:
    """The rows of a beat that last the ceiling of a fractional row length, by their place in the beat."""
    return tuple(index for index, row in enumerate(beat) if row > floor(row_ticks))
