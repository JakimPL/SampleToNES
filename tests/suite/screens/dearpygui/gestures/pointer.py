from typing import Dict, Final, Sequence, Tuple

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.bridge import ONE_FRAME
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.gestures.arrival import IMGUI_DOUBLE_CLICK_SECONDS, Arrival
from tests.suite.screens.dearpygui.gestures.constants import (
    HOLD_FRAMES,
    HOVER_FRAMES,
    REACH_TIMEOUT_SECONDS,
    RELEASE_FRAMES,
    SETTLE_FRAMES,
)
from tests.suite.screens.dearpygui.gestures.errors import GestureLostError, SlowFramesError
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.dearpygui.keys import keysym_of
from tests.suite.screens.dearpygui.xtest import MouseButton

SINGLE_PRESS: Final[int] = 1
DOUBLE_PRESS: Final[int] = 2
TRIPLE_PRESS: Final[int] = 3
HOVER_ARRIVAL_FRAMES: Final[int] = 5
DRAG_STEPS: Final[int] = 8

IMGUI_MOUSE_BUTTONS: Final[Dict[MouseButton, int]] = {
    MouseButton.LEFT: dpg.mvMouseButton_Left,
    MouseButton.RIGHT: dpg.mvMouseButton_Right,
    MouseButton.MIDDLE: dpg.mvMouseButton_Middle,
}


class Pointer(Arrival):
    """The pointer of a hand: presses, double-clicks, drags and hovering.

    It owns every gesture made with the buttons and builds each from `Arrival`'s steps: aim at the item,
    rest over it, press, confirm the press and settle. A click goes down and comes up in one go, and so do
    the presses of a double-click, so Dear ImGui reads each press on a frame of its own at any frame rate.
    The presses of a double-click then land two frames apart, and Dear ImGui counts them as one double-click
    while those frames take less than its double-click time between them. `Scrolling` reuses its hover and
    drag to reach scrollbars and the wheel.
    """

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
        try:
            self._settle(HOLD_FRAMES)
            self._confirm_keys(modifiers)
            self._press(item, MouseButton.LEFT, SINGLE_PRESS)
        finally:
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
        imgui_button = IMGUI_MOUSE_BUTTONS[MouseButton.LEFT]
        releases, double_clicks = self._bridge.ask(lambda: self._counts(imgui_button))
        self._device.click_button(MouseButton.LEFT, SINGLE_PRESS)
        self._device.button_down(MouseButton.LEFT)
        try:
            self._confirm(lambda: dpg.is_mouse_button_down(imgui_button), "The left button")
            self._require_double_click(imgui_button, releases, double_clicks)
            self._settle(frames)
        finally:
            self._device.button_up(MouseButton.LEFT)
        self._await_count(
            lambda: self._witness.button_releases(imgui_button),
            releases + DOUBLE_PRESS,
            "The left button",
        )
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
        deadline = self._bridge.deadline(REACH_TIMEOUT_SECONDS)
        while True:
            self._device.move(self._aim(item))
            self._bridge.frames(HOVER_FRAMES)
            if self._hovered_within(item, HOVER_ARRIVAL_FRAMES):
                return
            if deadline.passed():
                raise GestureLostError(
                    f"The pointer was aimed at {item!r} and the item reports no hover: "
                    f"something covers it, or the region it scrolls in clips it"
                )

    def _press(
        self,
        item: Item,
        button: MouseButton,
        count: int,
    ) -> None:
        self.hover(item)
        self._outlast_a_double_click()
        self._press_where_it_stands(button, count)
        self._last_release = self._application_seconds()
        self._settle(SETTLE_FRAMES)

    def _press_where_it_stands(
        self,
        button: MouseButton,
        count: int,
    ) -> None:
        """Presses ``button`` ``count`` times in one go where the pointer stands, and confirms Dear ImGui read
        every release, and the double-click when the presses are more than one.
        """
        imgui_button = IMGUI_MOUSE_BUTTONS[button]
        releases, double_clicks = self._bridge.ask(lambda: self._counts(imgui_button))
        self._device.click_button(button, count)
        running = self._await_count(
            lambda: self._witness.button_releases(imgui_button),
            releases + count,
            f"The {button.name.lower()} button",
        )
        if running and count > SINGLE_PRESS:
            self._require_double_click(imgui_button, releases, double_clicks)

    def _counts(self, imgui_button: int) -> Tuple[int, int]:
        """The releases and the double-clicks the witness counted of ``imgui_button`` so far."""
        return (
            self._witness.button_releases(imgui_button),
            self._witness.double_clicks(imgui_button),
        )

    def _require_double_click(
        self,
        imgui_button: int,
        releases: int,
        double_clicks: int,
    ) -> None:
        """Checks that Dear ImGui counted a double-click since the witness counted ``double_clicks`` of them.

        The presses came two frames apart, so a missing double-click says the display drew those frames
        more slowly than Dear ImGui's double-click time allows.

        Raises:
            SlowFramesError: If Dear ImGui counted the presses as separate clicks.
        """
        if self._bridge.ask(lambda: self._witness.double_clicks(imgui_button)) > double_clicks:
            return

        times = self._bridge.ask(lambda: self._witness.button_release_times(imgui_button))[releases:]
        took = f"{times[1] - times[0]:.2f} s" if len(times) > 1 else "longer than that"
        raise SlowFramesError(
            f"Dear ImGui counted no double-click: it counts two presses landing within "
            f"{IMGUI_DOUBLE_CLICK_SECONDS} s of each other, and the two frames between these took {took}"
        )

    def _press_at(
        self,
        point: Point,
        button: MouseButton,
        count: int,
    ) -> None:
        self.move_to(point)
        self._outlast_a_double_click()
        self._press_where_it_stands(button, count)
        self._last_release = self._application_seconds()
        self._settle(SETTLE_FRAMES)

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
        try:
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
        finally:
            self._device.button_up(MouseButton.LEFT)

        self._settle(RELEASE_FRAMES)
