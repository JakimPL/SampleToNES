from fractions import Fraction
from math import ceil, floor
from typing import Final, Tuple

HALF: Final[Fraction] = Fraction(1, 2)
SINGLE_ROW: Final[int] = 1


def nearest(value: Fraction) -> int:
    """The whole number closest to ``value``, a half rounding up."""
    return floor(value + HALF)


def split_by_halving(
    total: int,
    spans: Tuple[int, ...],
    *,
    row_ticks: Fraction,
) -> Tuple[int, ...]:
    """Shares a tick total among the rows of consecutive spans by halving them down to single rows.

    The spans are cut in two, the larger part first, so three spans part as two and one. Each part
    takes the share of the total nearest its exact length, and each part is then halved again. A
    single span is cut between its own rows. The surplus ticks therefore settle where a listener hears
    the strongest positions: the first half of a bar's beats, then the halves of those, and inside a
    beat its first row, then its middle, then its quarters.

    Every row of the spans lasts ``row_ticks`` exactly, and each part's share is held to what its rows
    can carry, so every row lasts the floor or the ceiling of ``row_ticks``.

    Args:
        total: The ticks the spans share, between the floor and the ceiling of their exact length.
        spans: The row count of each consecutive span, in order, each at least 1.
        row_ticks: The exact ticks one row lasts.

    Returns:
        Tuple[int, ...]: One tick count per row of the spans, together summing to ``total``.

    Raises:
        ValueError: If no span is given, a span holds no row, or ``total`` lies outside what the rows
            carry at the floor and the ceiling of ``row_ticks``.
    """
    if not spans:
        raise ValueError("At least one span is required to share a tick total")

    if any(span < SINGLE_ROW for span in spans):
        raise ValueError(f"Every span must hold at least 1 row, got {spans}")

    rows = sum(spans)
    if not rows * floor(row_ticks) <= total <= rows * ceil(row_ticks):
        raise ValueError(f"{rows} rows of {row_ticks} ticks each carry no total of {total}")

    return _halved(total, spans, row_ticks)


def _halved(
    total: int,
    spans: Tuple[int, ...],
    row_ticks: Fraction,
) -> Tuple[int, ...]:
    if len(spans) == 1:
        if spans[0] == SINGLE_ROW:
            return (total,)

        spans = (SINGLE_ROW,) * spans[0]

    middle = ceil(len(spans) / 2)
    first, second = spans[:middle], spans[middle:]
    first_rows, second_rows = sum(first), sum(second)
    share = nearest(total * Fraction(first_rows, first_rows + second_rows))
    lowest = max(first_rows * floor(row_ticks), total - second_rows * ceil(row_ticks))
    highest = min(first_rows * ceil(row_ticks), total - second_rows * floor(row_ticks))
    share = min(max(share, lowest), highest)
    return _halved(share, first, row_ticks) + _halved(total - share, second, row_ticks)
