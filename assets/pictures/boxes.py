from typing import Final, Sequence, Tuple

import numpy as np

from automation.dearpygui.geometry import Rect

RGB_CHANNELS: Final[int] = 3
COLOR_TOLERANCE: Final[float] = 1.5 / 255.0


class NothingChangedError(AssertionError):
    """Raised when two frames compared for a popup differ in no pixel, so no popup stands to picture."""


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


def changed_box(before: np.ndarray, after: np.ndarray) -> Rect:
    """The box around every pixel that differs between two frames, which is where a popup opened.

    A popup reports no box of its own, so the frame before it opened and the frame after are
    compared, and the difference is the popup with the highlight of whatever opened it.

    Raises:
        NothingChangedError: If no pixel differs.
    """
    changed = np.any(
        np.abs(after[:, :, :RGB_CHANNELS] - before[:, :, :RGB_CHANNELS]) > COLOR_TOLERANCE,
        axis=2,
    )
    rows = np.nonzero(changed.any(axis=1))[0]
    columns = np.nonzero(changed.any(axis=0))[0]
    if not rows.size:
        raise NothingChangedError("The two frames show the same picture, so nothing opened between them")

    left, right = int(columns.min()), int(columns.max())
    top, bottom = int(rows.min()), int(rows.max())
    return Rect(x=left, y=top, width=right - left + 1, height=bottom - top + 1)
