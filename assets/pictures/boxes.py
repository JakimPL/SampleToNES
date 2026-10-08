from typing import Sequence, Tuple

from automation.dearpygui.geometry import Rect


def union(rects: Sequence[Rect]) -> Rect:
    """The smallest box holding every box in ``rects``.

    Raises:
        ValueError: If ``rects`` is empty.
    """
    if not rects:
        raise ValueError("A union takes at least one box")

    left = min(rect.x for rect in rects)
    top = min(rect.y for rect in rects)
    right = max(rect.x + rect.width for rect in rects)
    bottom = max(rect.y + rect.height for rect in rects)
    return Rect(x=left, y=top, width=right - left, height=bottom - top)


def corner_box(rects: Sequence[Rect]) -> Rect:
    """The box from the frame's top left corner down and across to the farthest edge of ``rects``.

    Raises:
        ValueError: If ``rects`` is empty.
    """
    held = union(rects)
    return Rect(x=0, y=0, width=held.x + held.width, height=held.y + held.height)


def crop_box(
    rect: Rect,
    margin: int,
    *,
    width: int,
    height: int,
) -> Tuple[int, int, int, int]:
    """The pixel box ``margin`` pixels around ``rect``, kept inside a frame of ``width`` by ``height``.

    The box reads as an image library takes it: left, top, right and bottom, the last two exclusive.
    """
    left = max(0, int(rect.x) - margin)
    top = max(0, int(rect.y) - margin)
    right = min(width, int(rect.x + rect.width) + margin)
    bottom = min(height, int(rect.y + rect.height) + margin)
    return left, top, right, bottom
