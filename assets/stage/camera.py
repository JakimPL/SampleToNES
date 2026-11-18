from typing import Final, Optional

import numpy as np

from automation.dearpygui.geometry import Rect
from automation.dearpygui.items.reading import read_item
from automation.dearpygui.items.types import Item
from automation.frames import settled_frame
from automation.screen import Screen

STATUS_SECONDS: Final[float] = 15.0


class BoxlessItemError(AssertionError):
    """Raised when an item a maker frames reports no box."""


class Camera:
    """Reads what the screen shows for a maker: the frames it draws and the boxes of the items it frames.

    The first frame DearPyGui hands over after a readback is asked for is the bare clear color, so the
    first reading is taken and discarded. A frame is taken once the screen holds still, since a card
    fills and a status line clears a frame or two after the gesture that brought them.
    """

    def __init__(self, screen: Screen) -> None:
        self._screen = screen
        self._warm = False

    def rest(self) -> None:
        """Parks the pointer on the bare far end of the tab bar, where it lights nothing, and waits for the status
        bar to let go of the hint of whatever the pointer left, which it keeps for a while.
        """
        self._screen.hand.move_to(self._screen.menu.bare_spot())
        self._screen.bridge.expect(
            self._screen.status,
            "".__eq__,
            description="the status bar empty",
            timeout=STATUS_SECONDS,
        )

    def pixels(self) -> np.ndarray:
        """The frame drawn once the screen holds still, after the first readback of the process is discarded."""
        if not self._warm:
            self._screen.frame_pixels()
            self._warm = True

        return settled_frame(self._screen.bridge)

    def rect(self, item: Item) -> Rect:
        """The box ``item`` stands in on the screen.

        Raises:
            BoxlessItemError: If the item reports no box.
        """
        rect: Optional[Rect] = self._screen.bridge.ask(lambda: read_item(item).rect)
        if rect is None:
            raise BoxlessItemError(f"{item} reports no box to frame")

        return rect
