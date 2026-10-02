import time
from functools import partial
from typing import Callable, Dict, Final, Optional, Sequence

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.bridge import ONE_FRAME, Bridge, RenderThreadStoppedError
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.items import (
    Item,
    enclosing_regions,
    read_hovered,
    read_item,
    read_scroll,
    read_viewport,
    read_visible_box,
)
from tests.suite.screens.dearpygui.keys import (
    IMGUI_LEFT_CTRL,
    IMGUI_LEFT_SHIFT,
    IMGUI_LETTER_A,
    key_name,
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
HOVER_ARRIVAL_FRAMES: Final[int] = 5
REACH_TIMEOUT_SECONDS: Final[float] = 10.0
WHEEL_FRAMES: Final[int] = 1
SCROLL_NOTCH_LIMIT: Final[int] = 400
EDGE_INSET: Final[int] = 3
DRAG_STEPS: Final[int] = 8
IMGUI_MOUSE_BUTTONS: Final[Dict[MouseButton, int]] = {
    MouseButton.LEFT: dpg.mvMouseButton_Left,
    MouseButton.RIGHT: dpg.mvMouseButton_Right,
    MouseButton.MIDDLE: dpg.mvMouseButton_Middle,
}


class GestureLostError(AssertionError):
    """Raised when a gesture's input never reached the control it was aimed at."""


class Hand:
    """A user's hand on the application: the pointer and the keyboard of the scenario's display.

    A gesture first reads where its control stands, refusing one beyond a user's reach, and then
    plays the events a person makes. Every step waits whole frames, since the application reads
    input once a frame: the pointer rests over a control before pressing it, and a modifier is held
    a frame before the key it modifies goes down. A gesture that closes the application ends where
    the application stopped, which is how a scenario presses the button that leaves it.

    A gesture confirms that it arrived. The control reports the pointer resting on it before a
    button goes down, and the application reports every held button and named key down while it is
    held, so a press lost on the way fails where it was lost, and a scenario expecting nothing to
    happen learns that its gesture was made.
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
        """Rests the pointer over ``item`` until the item reports it.

        Raises:
            GestureLostError: If the item never reports the pointer resting on it.
        """
        self._device.move(self._aim(item))
        self._bridge.frames(HOVER_FRAMES)
        self._confirm_hover(item)

    def wheel(
        self,
        item: Item,
        notches: int,
    ) -> None:
        """Rests the pointer over ``item`` and turns the wheel ``notches`` notches, down for a positive count."""
        self.hover(item)
        self._turn_wheel(notches)
        self._settle(SETTLE_FRAMES)

    def scroll_into_view(self, item: Item) -> None:
        """Turns the wheel over the regions ``item`` scrolls in until the item stands whole in view.

        The nearest region that scrolls is moved first, at its right edge, and the regions around it
        after. The wheel moves a region that takes it: the first notch shows how far one notch carries
        the region, and each later turn takes as many notches as the distance left needs, the way a
        person spins the wheel toward a row. A region the wheel leaves alone is moved by dragging its
        scrollbar's grip to where the grip stands for the scroll the item needs.

        Raises:
            UnreachableError: If a region stops moving, or the wheel runs out of turns, first.
        """
        for region in self._bridge.ask(lambda: enclosing_regions(item)):
            self._scroll_within(item, region)

        self._settle(SETTLE_FRAMES)

    def _scroll_within(self, item: Item, region: Item) -> None:
        notch = 0.0
        for _ in range(SCROLL_NOTCH_LIMIT):
            distance = self._bridge.ask(lambda: _distance_from_view(item, region))
            before = self._bridge.ask(lambda: read_scroll(region))
            if distance == 0 or before.maximum == 0:
                return

            if before.by_wheel:
                self._device.move(self._bridge.ask(lambda: _wheel_point(region)))
                self._settle(HOVER_FRAMES)
                notches = max(1, int(abs(distance) // notch)) if notch > 0 else 1
                self._turn_wheel(notches if distance > 0 else -notches)
            else:
                start = self._bridge.ask(lambda: _grip_point(region, before.position))
                end = self._bridge.ask(lambda: _grip_point(region, before.position + distance))
                self._drag_between(start, end)
                notches = 1

            self._settle(ONE_FRAME)
            after = self._bridge.ask(lambda: read_scroll(region))
            if after == before:
                raise UnreachableError(f"{item!r} stays out of view: the region {region!r} stopped at {before}")

            notch = abs(after.position - before.position) / notches

        raise UnreachableError(f"{item!r} stays out of view after {SCROLL_NOTCH_LIMIT} turns of the wheel")

    def press_key(
        self,
        key: int,
        *,
        modifiers: Sequence[int],
    ) -> None:
        """Presses the Dear ImGui key ``key`` while holding the Dear ImGui keys in ``modifiers``."""
        for modifier in modifiers:
            self._device.key_down(keysym_of(modifier))
        if modifiers:
            self._settle(HOLD_FRAMES)
            self._confirm_keys(modifiers)

        self._device.key_down(keysym_of(key))
        self._settle(HOLD_FRAMES)
        self._confirm_keys([key])
        self._device.key_up(keysym_of(key))
        self._settle(RELEASE_FRAMES)
        for modifier in reversed(modifiers):
            self._device.key_up(keysym_of(modifier))

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
        imgui_button = IMGUI_MOUSE_BUTTONS[button]
        for _ in range(count):
            self._device.button_down(button)
            self._settle(HOLD_FRAMES)
            self._confirm(lambda: dpg.is_mouse_button_down(imgui_button), f"The {button.name.lower()} button")
            self._device.button_up(button)
            self._settle(RELEASE_FRAMES)

        self._settle(SETTLE_FRAMES)

    def _drag_between(self, start: Point, end: Point) -> None:
        """Presses the left button at ``start``, carries it to ``end`` over a few frames, and lets go there."""
        self._device.move(start)
        self._settle(HOVER_FRAMES)
        self._device.button_down(MouseButton.LEFT)
        self._settle(HOLD_FRAMES)
        for step in range(1, DRAG_STEPS + 1):
            self._device.move(
                Point(
                    x=start.x + round((end.x - start.x) * step / DRAG_STEPS),
                    y=start.y + round((end.y - start.y) * step / DRAG_STEPS),
                )
            )
            self._settle(ONE_FRAME)

        self._device.button_up(MouseButton.LEFT)
        self._settle(RELEASE_FRAMES)

    def _turn_wheel(self, notches: int) -> None:
        button = MouseButton.WHEEL_DOWN if notches > 0 else MouseButton.WHEEL_UP
        for _ in range(abs(notches)):
            self._device.button_down(button)
            self._settle(WHEEL_FRAMES)
            self._device.button_up(button)
            self._settle(WHEEL_FRAMES)

    def _tap(self, keysym: int) -> None:
        self._device.key_down(keysym)
        self._settle(HOLD_FRAMES)
        self._device.key_up(keysym)
        self._settle(RELEASE_FRAMES)

    def _confirm_hover(self, item: Item) -> None:
        """Waits a few frames for ``item`` to report the pointer resting on it, where its kind reports hover.

        Raises:
            GestureLostError: If the item never reports the pointer, which is a press bound elsewhere.
        """
        for _ in range(HOVER_ARRIVAL_FRAMES):
            if self._bridge.ask(lambda: read_hovered(item)) is not False:
                return

            self._bridge.frames(ONE_FRAME)

        raise GestureLostError(
            f"The pointer was aimed at {item!r} and the item reports no hover: "
            f"something covers it, or the region it scrolls in clips it"
        )

    def _confirm_keys(self, keys: Sequence[int]) -> None:
        for key in keys:
            self._confirm(partial(dpg.is_key_down, key), f"The key {key_name(key)}")

    def _confirm(
        self,
        is_down: Callable[[], bool],
        what: str,
    ) -> None:
        """Checks that the application reads a held button or key as down, unless the gesture closed it.

        Raises:
            GestureLostError: If the application reads it as up while it is held.
        """
        try:
            arrived = self._bridge.ask(is_down)
        except RenderThreadStoppedError:
            return

        if not arrived:
            raise GestureLostError(f"{what} is held on the display and the application reads it as up")

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


def _distance_from_view(item: Item, region: Item) -> float:
    """How far the region must scroll for ``item`` to stand whole in its view: down for a positive distance.

    Runs on the render thread.
    """
    item_box = read_item(item).rect
    region_box = read_item(region).rect
    if item_box is None or region_box is None:
        raise UnreachableError(f"{item!r} or the region {region!r} it scrolls in reports no box")

    below = item_box.y + item_box.height - (region_box.y + region_box.height)
    if below > 0:
        return below
    above = item_box.y - region_box.y
    if above < 0:
        return above

    return 0.0


def _wheel_point(region: Item) -> Point:
    """A pixel at the right edge of the part of ``region`` left in view, where its scrollbar stands.

    The middle of a region often lies over a smaller region it holds, which would take the wheel;
    the edge belongs to the region itself. Runs on the render thread.
    """
    visible = read_visible_box(region)
    if visible is None:
        raise UnreachableError(f"No part of the region {region!r} stands in view to turn the wheel over")

    viewport = read_viewport()
    return Point(
        x=round(viewport.x + visible.x + visible.width) - EDGE_INSET,
        y=round(viewport.y) + visible.center.y,
    )


def _grip_point(region: Item, scroll: float) -> Point:
    """The pixel at the middle of ``region``'s scrollbar grip while the region stands scrolled to ``scroll``.

    The grip spans the share of the content the region shows, and travels the rest of the track as
    the region scrolls from its top to its end. Runs on the render thread.
    """
    visible = read_visible_box(region)
    if visible is None:
        raise UnreachableError(f"No part of the region {region!r} stands in view to drag its scrollbar")

    reading = read_scroll(region)
    target = min(max(scroll, 0.0), reading.maximum)
    grip = visible.height * visible.height / (visible.height + reading.maximum)
    travel = visible.height - grip
    viewport = read_viewport()
    return Point(
        x=round(viewport.x + visible.x + visible.width) - EDGE_INSET,
        y=round(viewport.y + visible.y + grip / 2 + travel * target / reading.maximum),
    )
