from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple


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

    @classmethod
    def spanning(cls, rects: Sequence[Rect]) -> Rect:
        """The smallest box holding every box in ``rects``.

        Raises:
            ValueError: If ``rects`` is empty.
        """
        if not rects:
            raise ValueError("A span takes at least one box")

        left = min(rect.x for rect in rects)
        top = min(rect.y for rect in rects)
        right = max(rect.x + rect.width for rect in rects)
        bottom = max(rect.y + rect.height for rect in rects)
        return cls(x=left, y=top, width=right - left, height=bottom - top)

    @classmethod
    def from_origin_to(cls, rects: Sequence[Rect]) -> Rect:
        """The box from the screen's top left corner down and across to the farthest edge of ``rects``.

        Raises:
            ValueError: If ``rects`` is empty.
        """
        held = cls.spanning(rects)
        return cls(x=0, y=0, width=held.x + held.width, height=held.y + held.height)

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

    def pixel_box(self, margin: int, *, width: int, height: int) -> Tuple[int, int, int, int]:
        """The whole pixels ``margin`` pixels around this box, kept inside a frame of ``width`` by ``height``.

        The box reads as an image library takes it: left, top, right and bottom, the last two exclusive.
        """
        left = max(0, int(self.x) - margin)
        top = max(0, int(self.y) - margin)
        right = min(width, int(self.x + self.width) + margin)
        bottom = min(height, int(self.y + self.height) + margin)
        return left, top, right, bottom
