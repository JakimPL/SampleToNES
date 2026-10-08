from pathlib import Path
from typing import Callable, Final, List, Optional

import numpy as np
from PIL import Image

from assets.pictures.boxes import changed_box, crop_box, union
from assets.pictures.frames import to_image
from assets.pictures.jitter import is_jitter
from automation.dearpygui.geometry import Point, Rect
from automation.dearpygui.items.reading import read_item
from automation.dearpygui.items.types import Item
from automation.dearpygui.items.viewport import read_viewport
from automation.screen import Screen
from sampletones_application.tags.general import TAG_GLOBAL_TAB_INSTRUCTIONS

MARGIN: Final[int] = 8
OPENING_FRAMES: Final[int] = 5
FAR_END_INSET: Final[int] = 30
FORMAT: Final[str] = "WEBP"
LOSSLESS: Final[bool] = True
QUALITY: Final[int] = 100
METHOD: Final[int] = 6


class BoxlessItemError(AssertionError):
    """Raised when an item a picture is cropped around reports no box."""


class Pictures:
    """Keeps pictures of what the screen shows, cropped to what a page names and written where it is kept.

    The first frame DearPyGui hands over after a readback is asked for is the bare clear color, so
    the first reading is taken and discarded. Every picture is written lossless, so what the guide
    shows is what the screen drew.
    """

    def __init__(self, screen: Screen) -> None:
        self._screen = screen
        self._warm = False

    def window(self, target: Path) -> Path:
        """Writes the whole window to ``target``."""
        return write(to_image(self.pixels()), target)

    def around(self, target: Path, *items: Item) -> Path:
        """Writes the part of the window holding every one of ``items``, with a margin around them, to ``target``.

        Raises:
            BoxlessItemError: If one of the items reports no box.
        """
        rects = [self._rect(item) for item in items]
        return write(cropped(to_image(self.pixels()), union(rects)), target)

    def popup(self, target: Path, opening: Callable[[], None]) -> Path:
        """Writes the popup that ``opening`` opens, and the control that opened it, to ``target``.

        The frame before and the frame after the popup opened are compared, and the box around what
        changed is what is kept.
        """
        before = self.pixels()
        opening()
        self._screen.frames(OPENING_FRAMES)
        after = self.pixels()
        return write(cropped(to_image(after), changed_box(before, after)), target)

    def rest(self) -> None:
        """Parks the pointer on the bare far end of the tab bar, where it lights nothing and the status bar stays
        empty.
        """
        last_tab = self._rect(TAG_GLOBAL_TAB_INSTRUCTIONS)
        viewport = self._screen.bridge.ask(read_viewport)
        self._screen.hand.move_to(Point(x=round(viewport.width) - FAR_END_INSET, y=last_tab.center.y))

    def pixels(self) -> np.ndarray:
        """The next frame drawn, after the first readback of the process has been discarded."""
        if not self._warm:
            self._screen.frame_pixels()
            self._warm = True

        return self._screen.frame_pixels()

    def _rect(self, item: Item) -> Rect:
        rect: Optional[Rect] = self._screen.bridge.ask(lambda: read_item(item).rect)
        if rect is None:
            raise BoxlessItemError(f"{item} reports no box to picture")

        return rect


def cropped(image: Image.Image, rect: Rect) -> Image.Image:
    """The part of ``image`` holding ``rect`` with the margin around it."""
    return image.crop(crop_box(rect, MARGIN, width=image.width, height=image.height))


def write(image: Image.Image, target: Path) -> Path:
    """Writes ``image`` lossless to ``target``, making the folders on the way, and returns the target.

    A picture already kept at the target stands when the drawing differs from it by the renderer's
    jitter alone, so a run after no change to the interface leaves the repository as it was.
    """
    if target.is_file() and is_jitter(Image.open(target), image):
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, FORMAT, lossless=LOSSLESS, quality=QUALITY, method=METHOD)
    return target


def written_since(directory: Path, moment: float, suffix: str) -> List[Path]:
    """Every file with ``suffix`` under ``directory`` written at or after ``moment``, in path order."""
    return sorted(path for path in directory.rglob(f"*{suffix}") if path.stat().st_mtime >= moment)
