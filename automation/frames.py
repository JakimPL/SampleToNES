from typing import Final

import numpy as np

from automation.dearpygui.bridge import Bridge
from automation.dearpygui.geometry import Rect
from automation.dearpygui.screenshot import drawn_frame

PIXEL_CHANNELS: Final[int] = 4
RGB_CHANNELS: Final[int] = 3
COLOR_TOLERANCE: Final[float] = 1.5 / 255.0
SETTLE_GAP_FRAMES: Final[int] = 3
SETTLE_READINGS: Final[int] = 40


class NothingChangedError(AssertionError):
    """Raised when two frames compared for what opened between them differ in no pixel."""


class UnsettledScreenError(AssertionError):
    """Raised when the screen keeps changing while a reading waits for it to hold still."""


def frame_pixels(bridge: Bridge) -> np.ndarray:
    """The next frame the application draws, as rows of pixels of red, green, blue and alpha fractions."""
    frame = drawn_frame(bridge)
    return np.frombuffer(frame.pixels, dtype=np.float32).reshape(frame.height, frame.width, PIXEL_CHANNELS)


def settled_frame(bridge: Bridge) -> np.ndarray:
    """The frame drawn once the screen holds still: two readbacks a few frames apart read the same.

    A card fills and a status line clears a frame or two after the gesture that brought them, and a
    frame read in between shows the screen halfway.

    Raises:
        UnsettledScreenError: If the readbacks keep differing.
    """
    previous = frame_pixels(bridge)
    for _ in range(SETTLE_READINGS):
        bridge.frames(SETTLE_GAP_FRAMES)
        current = frame_pixels(bridge)
        if np.array_equal(previous, current):
            return current

        previous = current

    raise UnsettledScreenError(f"The screen kept changing over {SETTLE_READINGS} readings")


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
