from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np

from automation.frames import RGB_CHANNELS

Box = Tuple[int, int, int, int]
Size = Tuple[int, int]
Corner = Tuple[int, int]
Ground = Tuple[int, int, int]


class CompositionError(ValueError):
    """Raised when the panes stand too wide for the frame or too tall for its clear band."""


@dataclass(frozen=True)
class Layout:
    """A video frame of ``width`` by ``height`` pixels whose panes stand stacked ``gap`` pixels apart, each
    centered across, the stack centered down the band from ``top`` to ``bottom`` that the platform's overlays
    leave clear.
    """

    width: int
    height: int
    top: int
    bottom: int
    gap: int


def placements(sizes: Sequence[Size], layout: Layout) -> List[Corner]:
    """The top left corner each pane of ``sizes``, given as width and height, stands at in the frame.

    Raises:
        CompositionError: If a pane is wider than the frame or the stack taller than the clear band.
    """
    widest = max(width for width, _ in sizes)
    stack = sum(height for _, height in sizes) + layout.gap * (len(sizes) - 1)
    band = layout.bottom - layout.top
    if widest > layout.width:
        raise CompositionError(f"A pane {widest} px wide stands wider than the {layout.width} px frame")
    if stack > band:
        raise CompositionError(f"The panes stack {stack} px tall, more than the {band} px clear band")

    corners: List[Corner] = []
    top = layout.top + (band - stack) // 2
    for width, height in sizes:
        corners.append(((layout.width - width) // 2, top))
        top += height + layout.gap

    return corners


def composed(pixels: np.ndarray, boxes: Sequence[Box], layout: Layout, ground: Ground) -> np.ndarray:
    """The frame holding each box of ``pixels`` at its placement, on a ground of ``ground``.

    Args:
        pixels: The screen as rows of eight-bit red, green and blue levels.
        boxes: The panes cut from the screen, each as left, top, right and bottom, the last two exclusive.
        layout: The frame the panes are laid on.
        ground: The color the frame shows around the panes.

    Raises:
        CompositionError: If the panes stand too wide or too tall for the frame.
    """
    sizes = [(right - left, bottom - top) for left, top, right, bottom in boxes]
    frame = np.empty((layout.height, layout.width, RGB_CHANNELS), dtype=np.uint8)
    frame[:] = ground
    for (left, top, right, bottom), (x, y) in zip(boxes, placements(sizes, layout)):
        frame[y : y + bottom - top, x : x + right - left] = pixels[top:bottom, left:right]

    return frame
