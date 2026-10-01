import time
from typing import Final, Optional, Sequence

from tests.suite.screens.dearpygui.bridge import ONE_FRAME, Bridge, RenderThreadStoppedError
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.items import Item, read_viewport
from tests.suite.screens.dearpygui.keys import (
    IMGUI_LEFT_CTRL,
    IMGUI_LEFT_SHIFT,
    IMGUI_LETTER_A,
    keysym_of,
    keysym_of_character,
)
from tests.suite.screens.dearpygui.reach import UnreachableError, reachable
from tests.suite.screens.dearpygui.xtest import MouseButton, XTestDevice

HOVER_FRAMES: Final[int] = 2
HOLD_FRAMES: Final[int] = 2
RELEASE_FRAMES: Final[int] = 1
SETTLE_FRAMES: Final[int] = 2
SINGLE_PRESS: Final[int] = 1
DOUBLE_PRESS: Final[int] = 2
REACH_TIMEOUT_SECONDS: Final[float] = 10.0


class Hand:
    """A user's hand on the application: the pointer and the keyboard of the scenario's display.

    A gesture first reads where its control stands, refusing one beyond a user's reach, and then
    plays the events a person makes. Every step waits whole frames, since the application reads
    input once a frame: the pointer rests over a control before pressing it, and a modifier is held
    a frame before the key it modifies goes down. A gesture that closes the application ends where
    the application stopped, which is how a scenario presses the button that leaves it.
    """

    def __init__(
        self,
        bridge: Bridge,
        device: XTestDevice,
    ) -> None:
        self._bridge = bridge
        self._device = device

    def click(self, item: Item) -> None:
        """Presses ``item`` with the left button."""
        self._press(item, MouseButton.LEFT, SINGLE_PRESS)

    def double_click(self, item: Item) -> None:
        """Presses ``item`` twice in quick succession with the left button."""
        self._press(item, MouseButton.LEFT, DOUBLE_PRESS)

    def right_click(self, item: Item) -> None:
        """Presses ``item`` with the right button, the gesture that opens a context menu."""
        self._press(item, MouseButton.RIGHT, SINGLE_PRESS)

    def hover(self, item: Item) -> None:
        """Rests the pointer over ``item``."""
        self._device.move(self._aim(item))
        self._bridge.frames(HOVER_FRAMES)

    def press_key(
        self,
        key: int,
        *,
        modifiers: Sequence[int],
    ) -> None:
        """Presses the Dear ImGui key ``key`` while holding the Dear ImGui keys in ``modifiers``."""
        held = tuple(keysym_of(modifier) for modifier in modifiers)
        for keysym in held:
            self._device.key_down(keysym)
        if held:
            self._settle(HOLD_FRAMES)

        self._tap(keysym_of(key))
        for keysym in reversed(held):
            self._device.key_up(keysym)

        self._settle(SETTLE_FRAMES)

    def replace_text(
        self,
        item: Item,
        text: str,
    ) -> None:
        """Clicks the field ``item``, selects what it holds, and types ``text`` over it."""
        self.click(item)
        self.press_key(IMGUI_LETTER_A, modifiers=[IMGUI_LEFT_CTRL])
        self.type_text(text)

    def type_text(self, text: str) -> None:
        """Types ``text`` into whatever holds the keyboard, one character a frame."""
        shift = keysym_of(IMGUI_LEFT_SHIFT)
        for character in text:
            keysym = keysym_of_character(character)
            shifted = self._device.needs_shift(keysym)
            if shifted:
                self._device.key_down(shift)

            self._tap(keysym)
            if shifted:
                self._device.key_up(shift)

        self._settle(SETTLE_FRAMES)

    def _press(
        self,
        item: Item,
        button: MouseButton,
        count: int,
    ) -> None:
        self.hover(item)
        for _ in range(count):
            self._device.button_down(button)
            self._settle(HOLD_FRAMES)
            self._device.button_up(button)
            self._settle(RELEASE_FRAMES)

        self._settle(SETTLE_FRAMES)

    def _tap(self, keysym: int) -> None:
        self._device.key_down(keysym)
        self._settle(HOLD_FRAMES)
        self._device.key_up(keysym)
        self._settle(RELEASE_FRAMES)

    def _settle(self, count: int) -> None:
        """Lets ``count`` frames pass once a gesture is under way, or none once it closed the application."""
        try:
            self._bridge.frames(count)
        except RenderThreadStoppedError:
            return

    def _aim(self, item: Item) -> Point:
        """The screen pixel at the middle of ``item``, once a user could press it and it holds still.

        A control takes frames to appear after the gesture that brings it, and a window sized by its
        content settles its place over its first frames. The hand waits until the control is in reach
        and stands where it stood a frame before, the way a person waits for a dialog to stop moving,
        and reports why it stayed out of reach once the wait runs out.
        """

        def read() -> Point:
            center = reachable(item).center
            viewport = read_viewport()
            return Point(
                x=round(viewport.x) + center.x,
                y=round(viewport.y) + center.y,
            )

        deadline = time.monotonic() + REACH_TIMEOUT_SECONDS
        previous: Optional[Point] = None
        while True:
            try:
                point = self._bridge.ask(read)
            except UnreachableError:
                if time.monotonic() >= deadline:
                    raise
                point = None

            if point is not None and point == previous:
                return point
            if time.monotonic() >= deadline:
                raise UnreachableError(f"{item!r} kept moving: it stood at {previous} and then at {point}")

            previous = point
            self._bridge.frames(ONE_FRAME)
