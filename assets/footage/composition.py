import math
from dataclasses import dataclass
from typing import Final, List, Sequence, Tuple

import numpy as np
from PIL import Image

from automation.frames import RGB_CHANNELS

RESAMPLING: Final[Image.Resampling] = Image.Resampling.LANCZOS

Box = Tuple[int, int, int, int]
Size = Tuple[int, int]
Ground = Tuple[int, int, int]


class CompositionError(ValueError):
    """Raised when the panes stand too wide for the frame or too tall for its clear band."""


@dataclass(frozen=True)
class Layout:
    """A video frame of ``width`` by ``height`` pixels whose panes stand stacked ``gap`` pixels apart and at least
    as far from the frame's sides, each centered across, the stack enlarged to fill and centered down the band
    from ``top`` to ``bottom`` that the platform's overlays leave clear.
    """

    width: int
    height: int
    top: int
    bottom: int
    gap: int


@dataclass(frozen=True)
class Placement:
    """A pane laid on the frame: its top left corner and the size it is drawn at."""

    x: int
    y: int
    width: int
    height: int


def enlargement(sizes: Sequence[Size], layout: Layout) -> float:
    """How much the panes of ``sizes``, given as width and height, are enlarged by: as far as the frame's width
    within its side gaps and its clear band allow, the gaps kept as the layout sets them.

    Raises:
        CompositionError: If a pane is wider than the frame within its side gaps or the stack taller than the
            clear band.
    """
    widest = max(width for width, _ in sizes)
    stacked = sum(height for _, height in sizes)
    across = layout.width - 2 * layout.gap
    room = layout.bottom - layout.top - layout.gap * (len(sizes) - 1)
    if widest > across:
        raise CompositionError(f"A pane {widest} px wide stands wider than the {across} px the frame holds")
    if stacked > room:
        raise CompositionError(f"The panes stack {stacked} px tall, more than the {room} px the clear band holds")

    return min(across / widest, room / stacked)


def placements(sizes: Sequence[Size], layout: Layout) -> List[Placement]:
    """Where each pane of ``sizes`` stands in the frame, enlarged by :func:`enlargement`.

    Raises:
        CompositionError: If a pane is wider than the frame or the stack taller than the clear band.
    """
    factor = enlargement(sizes, layout)
    drawn = [(math.floor(width * factor), math.floor(height * factor)) for width, height in sizes]
    stack = sum(height for _, height in drawn) + layout.gap * (len(drawn) - 1)
    top = layout.top + (layout.bottom - layout.top - stack) // 2
    laid: List[Placement] = []
    for width, height in drawn:
        laid.append(Placement(x=(layout.width - width) // 2, y=top, width=width, height=height))
        top += height + layout.gap

    return laid


def composed(pixels: np.ndarray, boxes: Sequence[Box], layout: Layout, ground: Ground) -> np.ndarray:
    """The frame holding each box of ``pixels``, enlarged and laid at its placement, on a ground of ``ground``.

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
    for (left, top, right, bottom), placement in zip(boxes, placements(sizes, layout)):
        pane = pixels[top:bottom, left:right]
        if pane.shape[:2] != (placement.height, placement.width):
            pane = np.asarray(Image.fromarray(pane).resize((placement.width, placement.height), RESAMPLING))
        frame[placement.y : placement.y + placement.height, placement.x : placement.x + placement.width] = pane

    return frame
