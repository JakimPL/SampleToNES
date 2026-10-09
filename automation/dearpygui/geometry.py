from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


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

    def overlap(self, other: Rect) -> Optional[Rect]:
        """The part of this box ``other`` covers too, or ``None`` where the two do not meet."""
        left = max(self.x, other.x)
        top = max(self.y, other.y)
        right = min(self.x + self.width, other.x + other.width)
        bottom = min(self.y + self.height, other.y + other.height)
        if right <= left or bottom <= top:
            return None

        return Rect(x=left, y=top, width=right - left, height=bottom - top)

    def holds(self, point: Point) -> bool:
        """Whether ``point`` lies within this box, edges included."""
        return self.x <= point.x <= self.x + self.width and self.y <= point.y <= self.y + self.height

    def contains(self, other: Rect) -> bool:
        """Whether ``other`` lies within this box, edges included."""
        return (
            self.x <= other.x
            and self.y <= other.y
            and other.x + other.width <= self.x + self.width
            and other.y + other.height <= self.y + self.height
        )
