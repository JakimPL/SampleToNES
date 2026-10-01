from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Point:
    """A position on the screen, in whole pixels from its top left corner."""

    x: int
    y: int


@dataclass(frozen=True)
class Rect:
    """A box on the screen: its top left corner and its size, in pixels."""

    x: float
    y: float
    width: float
    height: float

    @classmethod
    def of(
        cls,
        corner: Sequence[float],
        size: Sequence[float],
    ) -> Rect:
        """The box standing at ``corner`` with ``size``, as DearPyGui reports both."""
        return cls(
            x=corner[0],
            y=corner[1],
            width=size[0],
            height=size[1],
        )

    @property
    def center(self) -> Point:
        """The pixel a pointer aims at to land on the box."""
        return Point(
            x=round(self.x + self.width / 2),
            y=round(self.y + self.height / 2),
        )

    def contains(self, other: Rect) -> bool:
        """Whether ``other`` lies within this box, edges included."""
        return (
            self.x <= other.x
            and self.y <= other.y
            and other.x + other.width <= self.x + self.width
            and other.y + other.height <= self.y + self.height
        )
