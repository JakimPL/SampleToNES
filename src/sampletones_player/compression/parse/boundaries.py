from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, List, Tuple


@dataclass(frozen=True)
class Boundaries:
    """The ticks a token starts on, read forwards and backwards from every tick of a plane.

    A loop re-enters the stream partway through, so the tick it re-enters at holds a token of
    its own and nothing spans across it. Knowing the nearest boundary either side of a tick is
    what keeps that true while the cheapest reading is searched for.

    Attributes:
        entries: The ticks a token is required to start on.
        previous: The nearest boundary at or before each tick.
        following: The nearest boundary after each tick, the plane's end standing in beyond the
            last of them.
    """

    entries: FrozenSet[int]
    previous: Tuple[int, ...]
    following: Tuple[int, ...]

    @classmethod
    def across(cls, ticks: int, entries: FrozenSet[int]) -> Boundaries:
        """Reads the boundaries of a plane into the two lookups a parse asks them by.

        Args:
            ticks: The ticks the plane covers.
            entries: The ticks a token is required to start on.

        Returns:
            Boundaries: The entries and the nearest one either side of every tick.
        """
        previous: List[int] = [0] * (ticks + 1)
        for position in range(1, ticks + 1):
            previous[position] = position - 1 if position - 1 in entries else previous[position - 1]

        following: List[int] = [ticks] * (ticks + 1)
        for position in range(ticks - 1, -1, -1):
            following[position] = position + 1 if position + 1 in entries else following[position + 1]

        return cls(
            entries=entries,
            previous=tuple(previous),
            following=tuple(following),
        )
