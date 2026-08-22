from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import List, Tuple

from sampletones_player.specification.compression import BYTE_VALUES


@dataclass(frozen=True)
class PlaneIndex:
    """A plane alongside the two readings of it every match is decided by.

    A phrase is stored at one pitch and played at any, so what identifies it is the step from
    each value to the next rather than the values themselves. The runs answer the other half:
    how far a value carries once a phrase has played its last, which is how a token states a
    note that outlasts its envelope.

    Attributes:
        plane: The values the plane plays, one per tick.
        differences: The step from each value to the next.
        runs: How many ticks the value at each position holds for.
    """

    plane: bytes
    differences: bytes
    runs: Tuple[int, ...]

    @classmethod
    def from_plane(cls, plane: bytes) -> PlaneIndex:
        """Reads a plane into the form matching is decided against.

        Args:
            plane: The values the plane plays, one per tick.

        Returns:
            PlaneIndex: The plane, its steps and its runs.
        """
        differences = bytes((following - value) % BYTE_VALUES for value, following in pairwise(plane))
        runs: List[int] = [1] * len(plane)
        for position in range(len(plane) - 2, -1, -1):
            if plane[position] == plane[position + 1]:
                runs[position] = runs[position + 1] + 1

        return cls(
            plane=plane,
            differences=differences,
            runs=tuple(runs),
        )

    @property
    def ticks(self) -> int:
        """The ticks the plane covers."""
        return len(self.plane)
