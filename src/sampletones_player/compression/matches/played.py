from sampletones_player.compression.matches.index import PlaneIndex


def _common_prefix(
    plane: bytes,
    position: int,
    expected: bytes,
    usable: int,
) -> int:
    for offset in range(usable):
        if plane[position + offset] != expected[offset]:
            return offset

    return usable


def _matched_ticks(
    plane: bytes,
    position: int,
    expected: bytes,
    usable: int,
) -> int:
    """The ticks the plane agrees with ``expected`` for, out of the ``usable`` it may play."""
    if plane.startswith(expected[:usable], position):
        return usable

    return _common_prefix(
        plane,
        position,
        expected,
        usable,
    )


def _held_ticks(
    index: PlaneIndex,
    position: int,
    expected: bytes,
    limit: int,
) -> int:
    """The ticks a phrase covers once it has played out, its final value carrying onwards."""
    end = position + len(expected)
    if len(expected) == limit or index.plane[end] != expected[-1]:
        return len(expected)

    return min(limit, len(expected) + index.runs[end])


def played_ticks(
    index: PlaneIndex,
    position: int,
    expected: bytes,
    limit: int,
) -> int:
    """The ticks the plane plays of ``expected`` from ``position``.

    A phrase matches for as long as the plane agrees with it, and a phrase the plane plays whole
    keeps covering ticks for as long as the value it ended on holds — which is the note that
    outlasts its envelope, stated by the one token.

    Args:
        index: The plane and the two readings of it matching is decided against.
        position: The tick the phrase would start at.
        expected: The values the phrase plays, already at the shift it is played at.
        limit: The most ticks a token may cover from there.

    Returns:
        int: The ticks the phrase covers, which is none where the plane parts from it at once.
    """
    usable = min(len(expected), limit)
    played = _matched_ticks(
        index.plane,
        position,
        expected,
        usable,
    )
    if played < usable or usable < len(expected):
        return played

    return _held_ticks(
        index,
        position,
        expected,
        limit,
    )
