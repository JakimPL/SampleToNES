from typing import List, Sequence, Tuple


def _divide_rounding_up(dividend: int, divisor: int) -> int:
    """Divides two integers, carrying a fractional result up to the next integer."""
    return -(-dividend // divisor)


def distribute_proportionally(
    total: int,
    lengths: Sequence[int],
) -> Tuple[int, ...]:
    """Shares a tick total among consecutive spans in proportion to their row counts.

    Each span ends at a boundary rounded up from its exact share, so where a share falls
    between two integers the surplus tick goes to the earlier span. Over a pattern this
    puts the longer rows on the earlier, metrically stronger positions.

    Only the floor and the ceiling of the average per row ever appear, which is what lets
    a caller hold every row within an engine's speed range by bounding ``total`` alone.

    Args:
        total: The tick count the spans share.
        lengths: The row count of each span, in order, each at least 1.

    Returns:
        Tuple[int, ...]: One tick total per span, together summing to ``total``.

    Raises:
        ValueError: If no span is given, or a span holds fewer than one row.
    """
    if not lengths:
        raise ValueError("At least one span is required to share a tick total")

    if any(length < 1 for length in lengths):
        raise ValueError(f"Every span must hold at least 1 row, got {tuple(lengths)}")

    rows = sum(lengths)
    shares: List[int] = []
    cumulative = 0
    boundary = 0
    for length in lengths:
        cumulative += length
        previous, boundary = boundary, _divide_rounding_up(total * cumulative, rows)
        shares.append(boundary - previous)

    return tuple(shares)


def distribute_by_halving(total: int, rows: int) -> Tuple[int, ...]:
    """Shares a tick total among rows by halving the span down to single rows.

    The earlier half takes the extra row where the count is odd and the surplus tick
    where the share is fractional, so within a beat the longer rows fall on the positions
    a listener hears as strong: the first row, then the halfway row, then the quarters.

    Args:
        total: The tick count the rows share.
        rows: How many rows share it, at least 1.

    Returns:
        Tuple[int, ...]: One tick count per row, together summing to ``total``.

    Raises:
        ValueError: If fewer than one row is given.
    """
    if rows < 1:
        raise ValueError(f"rows must be at least 1, got {rows}")

    if rows == 1:
        return (total,)

    left = _divide_rounding_up(rows, 2)
    right = rows - left
    halves = distribute_proportionally(total, (left, right))

    return distribute_by_halving(halves[0], left) + distribute_by_halving(halves[1], right)
