import time
from contextlib import suppress
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
    read_pointer,
    read_region_view,
    read_scroll,
    read_viewport,
    read_visible_box,
)
from tests.suite.screens.dearpygui.keys import (
    IMGUI_BACKSPACE,
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
TRIPLE_PRESS: Final[int] = 3
HOVER_ARRIVAL_FRAMES: Final[int] = 5
ARRIVAL_FRAMES: Final[int] = 10
REACH_TIMEOUT_SECONDS: Final[float] = 10.0
WHEEL_FRAMES: Final[int] = 1
SCROLL_NOTCH_LIMIT: Final[int] = 100
EDGE_INSET: Final[int] = 3
IMGUI_DOUBLE_CLICK_SECONDS: Final[float] = 0.30
DRAG_STEPS: Final[int] = 8
GRIP_MARGIN_PIXELS: Final[float] = 8.0
GRIP_DRAGS: Final[int] = 4
IMGUI_GRAB_MIN_SIZE: Final[float] = 12.0
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
        self._last_release: Optional[float] = None

    def click(self, item: Item) -> None:
        """Presses ``item`` with the left button."""
        self._press(item, MouseButton.LEFT, SINGLE_PRESS)

    def click_holding(
        self,
        item: Item,
        modifiers: Sequence[int],
    ) -> None:
        """Presses ``item`` with the left button while holding the Dear ImGui keys in ``modifiers``.

        The keys go down a frame before the button and come up once the press has settled, which is
        how a person makes a Ctrl-click, so an application reading them while it answers the press
        finds them held.
        """
        for modifier in modifiers:
            self._device.key_down(keysym_of(modifier))
        self._settle(HOLD_FRAMES)
        self._confirm_keys(modifiers)

        self._press(item, MouseButton.LEFT, SINGLE_PRESS)

        for modifier in reversed(modifiers):
            self._device.key_up(keysym_of(modifier))
        self._settle(SETTLE_FRAMES)

    def double_click(self, item: Item) -> None:
        """Presses ``item`` twice in quick succession with the left button."""
        self._press(item, MouseButton.LEFT, DOUBLE_PRESS)

    def double_click_held(
        self,
        item: Item,
        *,
        frames: int,
    ) -> None:
        """Presses ``item`` twice with the left button, holding the second press down for ``frames`` frames.

        A person lets go of a click some frames after pressing it, and the double-click is answered
        as the second press goes down, so whatever the answer brings under the pointer meets a held
        button.
        """
        self.hover(item)
        self._outlast_a_double_click()
        self._press_once(MouseButton.LEFT, HOLD_FRAMES)
        self._press_once(MouseButton.LEFT, frames)
        self._last_release = self._application_seconds()
        self._settle(SETTLE_FRAMES)

    def right_click(self, item: Item) -> None:
        """Presses ``item`` with the right button, the gesture that opens a context menu."""
        self._press(item, MouseButton.RIGHT, SINGLE_PRESS)

    def click_at(self, point: Point) -> None:
        """Presses the left button at ``point`` of the viewport, for a target DearPyGui reports a position alone for.

        The press confirms it reached the application, while what it landed on is for the scenario
        to read from what the press changed.
        """
        self._press_at(point, MouseButton.LEFT, SINGLE_PRESS)

    def double_click_at(self, point: Point) -> None:
        """Presses the left button twice in quick succession at ``point`` of the viewport."""
        self._press_at(point, MouseButton.LEFT, DOUBLE_PRESS)

    def right_click_at(self, point: Point) -> None:
        """Presses the right button at ``point`` of the viewport, for a menu a place offers rather than an item."""
        self._press_at(point, MouseButton.RIGHT, SINGLE_PRESS)

    def triple_click_at(self, point: Point) -> None:
        """Presses the left button three times in quick succession at ``point`` of the viewport."""
        self._press_at(point, MouseButton.LEFT, TRIPLE_PRESS)

    def move_to(self, point: Point) -> None:
        """Rests the pointer at ``point`` of the viewport."""
        self._device.move(self._on_display(point))
        self._settle(HOVER_FRAMES)

    def drag(self, start: Point, end: Point) -> None:
        """Presses the left button at ``start`` of the viewport, carries it to ``end`` over a few frames, and lets go.

        The press is confirmed held as the pointer sets off, so a drag the application never saw
        fails where it was lost.
        """
        self._outlast_a_double_click()
        self._drag_between(self._on_display(start), self._on_display(end))
        self._last_release = self._application_seconds()
        self._settle(SETTLE_FRAMES)

    def hover(self, item: Item) -> None:
        """Rests the pointer over ``item`` until the item reports it.

        Raises:
            GestureLostError: If the item never reports the pointer resting on it.
        """
        deadline = time.monotonic() + REACH_TIMEOUT_SECONDS
        while True:
            self._device.move(self._aim(item))
            self._bridge.frames(HOVER_FRAMES)
            if self._hovered_within(item, HOVER_ARRIVAL_FRAMES):
                return
            if time.monotonic() >= deadline:
                raise GestureLostError(
                    f"The pointer was aimed at {item!r} and the item reports no hover: "
                    f"something covers it, or the region it scrolls in clips it"
                )

    def wheel(
        self,
        item: Item,
        notches: int,
    ) -> None:
        """Rests the pointer over ``item`` and turns the wheel ``notches`` notches, down for a positive count."""
        self.hover(item)
        self._turn_wheel(notches)
        self._settle(SETTLE_FRAMES)

    def wheel_at(
        self,
        point: Point,
        notches: int,
    ) -> None:
        """Rests the pointer at viewport point ``point`` and turns the wheel ``notches`` notches, down if positive."""
        self.move_to(point)
        self._turn_wheel(notches)
        self._settle(SETTLE_FRAMES)

    def turn_wheel_over(
        self,
        region: Item,
        notches: int,
    ) -> None:
        """Turns the wheel ``notches`` notches over the right edge of ``region``, down for a positive count.

        The pointer goes where it goes whatever stands open, so the gesture reports nothing; the
        scenario reads what the turn moved.
        """
        self._device.move(self._bridge.ask(lambda: _wheel_point(region)))
        self._settle(HOVER_FRAMES)
        self._turn_wheel(notches)
        self._settle(SETTLE_FRAMES)

    def scroll_to_end(self, region: Item) -> None:
        """Drags the grip of ``region``'s scrollbar to the bottom, as a person reaches the end of a long list.

        A list drawing only the rows in view settles its length as it scrolls, so the grip is dragged
        again while the end moves on, and a turn of the wheel takes up the pixels the grip's whole
        steps leave over.

        Raises:
            UnreachableError: If the region stands short of its end afterwards.
        """
        self.scroll_into_view(region)
        for _ in range(GRIP_DRAGS):
            before = self._bridge.ask(lambda: read_scroll(region))
            if before.position >= before.maximum:
                return

            start = self._bridge.ask(partial(_grip_point, region, before.position))
            end = self._bridge.ask(partial(_grip_point, region, before.maximum + GRIP_MARGIN_PIXELS))
            self._drag_between(start, end)
            self._settle(SETTLE_FRAMES)

        short = self._bridge.ask(lambda: read_scroll(region))
        if short.position < short.maximum and short.by_wheel:
            self.turn_wheel_over(region, 1)

        after = self._bridge.ask(lambda: read_scroll(region))
        if after.position < after.maximum:
            raise UnreachableError(f"The region {region!r} stands short of its end at {after}")

    def scroll_into_view(self, item: Item) -> None:
        """Turns the wheel over the regions ``item`` scrolls in until the item stands whole in view.

        The nearest region that scrolls is moved first, at its right edge, and the regions around it
        after. The wheel moves a region that takes it: the first notch shows how far one notch carries
        the region, and each later turn takes as many notches as the distance left needs, the way a
        person spins the wheel toward a row. A region the wheel leaves alone is moved by dragging its
        scrollbar's grip to where the grip stands for the scroll the item needs, and a few pixels on,
        since the grip moves in whole pixels and each of them scrolls further than one.

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
                margin = GRIP_MARGIN_PIXELS if distance > 0 else -GRIP_MARGIN_PIXELS
                start = self._bridge.ask(partial(_grip_point, region, before.position))
                end = self._bridge.ask(partial(_grip_point, region, before.position + distance + margin))
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
        """Clicks the field ``item``, selects what it holds, deletes it, and types ``text`` in its place."""
        self.click(item)
        self.press_key(IMGUI_LETTER_A, modifiers=[IMGUI_LEFT_CTRL])
        self.press_key(IMGUI_BACKSPACE, modifiers=[])
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
        self._outlast_a_double_click()
        for _ in range(count):
            self._press_once(button, HOLD_FRAMES)

        self._last_release = self._application_seconds()
        self._settle(SETTLE_FRAMES)

    def _press_once(
        self,
        button: MouseButton,
        frames: int,
    ) -> None:
        """Holds ``button`` down where the pointer stands for ``frames`` frames, then lets it go."""
        imgui_button = IMGUI_MOUSE_BUTTONS[button]
        self._device.button_down(button)
        self._settle(frames)
        self._confirm(lambda: dpg.is_mouse_button_down(imgui_button), f"The {button.name.lower()} button")
        self._device.button_up(button)
        self._settle(RELEASE_FRAMES)

    def _outlast_a_double_click(self) -> None:
        """Waits until the last press lies further back than a double-click reaches, in the application's clock.

        A person's next gesture comes later than that, while frames drawn quickly bring it within
        reach, where Dear ImGui counts it with the clicks before it.
        """
        last = self._last_release
        if last is None:
            return

        while float(self._bridge.ask(dpg.get_total_time)) - last < IMGUI_DOUBLE_CLICK_SECONDS:
            self._bridge.frames(ONE_FRAME)

    def _application_seconds(self) -> Optional[float]:
        """The application's clock, or ``None`` once a gesture has closed the application."""
        try:
            return float(self._bridge.ask(dpg.get_total_time))
        except RenderThreadStoppedError:
            return None

    def _press_at(
        self,
        point: Point,
        button: MouseButton,
        count: int,
    ) -> None:
        self.move_to(point)
        self._outlast_a_double_click()
        for _ in range(count):
            self._press_once(button, HOLD_FRAMES)

        self._last_release = self._application_seconds()
        self._settle(SETTLE_FRAMES)

    def _on_display(self, point: Point) -> Point:
        """The display pixel at ``point`` of the viewport."""
        viewport = self._bridge.ask(read_viewport)
        return Point(x=round(viewport.x) + point.x, y=round(viewport.y) + point.y)

    def _drag_between(self, start: Point, end: Point) -> None:
        """Presses the left button at display pixel ``start``, carries it to ``end`` over a few frames, and lets go.

        Each step waits until the application reads the pointer where the step put it, so every
        point the drag passes through reaches the application while the button is down, and the
        pointer rests at ``end`` a few frames before the button comes up, as a person stops before
        letting go.
        """
        self._device.move(start)
        self._settle(HOVER_FRAMES)
        self._device.button_down(MouseButton.LEFT)
        self._settle(HOLD_FRAMES)
        self._confirm(lambda: dpg.is_mouse_button_down(dpg.mvMouseButton_Left), "The left button")

        for step in range(1, DRAG_STEPS + 1):
            point = Point(
                x=start.x + round((end.x - start.x) * step / DRAG_STEPS),
                y=start.y + round((end.y - start.y) * step / DRAG_STEPS),
            )
            self._device.move(point)
            self._settle(ONE_FRAME)
            self._confirm_pointer(point)

        self._settle(HOLD_FRAMES)
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

    def _hovered_within(self, item: Item, frames: int) -> bool:
        """Whether ``item`` reports the pointer resting on it within ``frames`` frames, or reports no hover at all.

        An item standing in a tree that rebuilds reports no hover until the rebuild lets it go, which
        is why the hover is aimed again until the reach time runs out.
        """
        for _ in range(frames):
            if self._bridge.ask(lambda: read_hovered(item)) is not False:
                return True

            self._bridge.frames(ONE_FRAME)

        return False

    def _confirm_pointer(self, point: Point) -> None:
        """Waits a few frames for the application to read the pointer at display pixel ``point``.

        Raises:
            GestureLostError: If the application reads the pointer elsewhere throughout.
        """
        viewport = self._bridge.ask(read_viewport)
        expected = Point(x=point.x - round(viewport.x), y=point.y - round(viewport.y))
        for _ in range(ARRIVAL_FRAMES):
            try:
                if self._bridge.ask(read_pointer) == expected:
                    return
            except RenderThreadStoppedError:
                return

            self._settle(ONE_FRAME)

        raise GestureLostError(f"The pointer was moved to {expected} and the application reads it elsewhere")

    def _confirm_keys(self, keys: Sequence[int]) -> None:
        for key in keys:
            self._confirm(partial(dpg.is_key_down, key), f"The key {key_name(key)}")

    def _confirm(
        self,
        is_down: Callable[[], bool],
        what: str,
    ) -> None:
        """Checks that the application reads a held button or key as down, unless the gesture closed it.

        A display busy with other work hands the press on a few frames late, so the check reads it
        once a frame for a few frames while it stays held.

        Raises:
            GestureLostError: If the application reads it as up throughout.
        """
        for _ in range(ARRIVAL_FRAMES):
            try:
                if self._bridge.ask(is_down):
                    return
            except RenderThreadStoppedError:
                return

            self._settle(ONE_FRAME)

        raise GestureLostError(f"{what} is held on the display and the application reads it as up")

    def _settle(self, count: int) -> None:
        """Lets ``count`` frames pass once a gesture is under way, or none once it closed the application."""
        with suppress(RenderThreadStoppedError):
            self._bridge.frames(count)

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
    region_box = read_region_view(region)
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

    The grip spans the share of the content the region shows, held at Dear ImGui's smallest grip,
    and travels the rest of the track as the region scrolls from its top to its end. The track spans
    the region's whole height, so the region stands whole in view for its grip to be dragged. Runs on
    the render thread.
    """
    box = read_item(region).rect
    if box is None:
        raise UnreachableError(f"The region {region!r} reports no box to drag its scrollbar in")

    reading = read_scroll(region)
    target = min(max(scroll, 0.0), reading.maximum)
    grip = min(max(box.height * box.height / (box.height + reading.maximum), IMGUI_GRAB_MIN_SIZE), box.height)
    travel = box.height - grip
    viewport = read_viewport()
    return Point(
        x=round(viewport.x + box.x + box.width) - EDGE_INSET,
        y=round(viewport.y + box.y + grip / 2 + travel * target / reading.maximum),
    )
