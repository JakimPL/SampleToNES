import time
from contextlib import suppress
from functools import partial
from typing import Callable, Final, Optional, Sequence

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.bridge import ONE_FRAME, Bridge, RenderThreadStoppedError
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.gestures.constants import REACH_TIMEOUT_SECONDS
from tests.suite.screens.dearpygui.gestures.errors import GestureLostError
from tests.suite.screens.dearpygui.items.reading import read_hovered
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.dearpygui.items.viewport import read_pointer, read_viewport
from tests.suite.screens.dearpygui.keys import key_name
from tests.suite.screens.dearpygui.reach import UnreachableError, reachable
from tests.suite.screens.dearpygui.xtest import XTestDevice

ARRIVAL_FRAMES: Final[int] = 10
IMGUI_DOUBLE_CLICK_SECONDS: Final[float] = 0.30


class Arrival:
    """The part of a hand that lets frames pass and confirms that its input reached DearPyGui.

    It owns the bridge, the display's input device and the time of the last release. It aims at an item
    once the item stands in reach and holds still, waits out a double-click window, and confirms
    that the pointer, a button or a key reads as held. `Pointer` and `Keyboard` build their gestures
    on these steps, and `Scrolling` reaches them through `Pointer`.
    """

    def __init__(
        self,
        bridge: Bridge,
        device: XTestDevice,
    ) -> None:
        self._bridge = bridge
        self._device = device
        self._last_release: Optional[float] = None

    def _settle(self, count: int) -> None:
        """Lets ``count`` frames pass once a gesture is under way, or none once it closed the application."""
        with suppress(RenderThreadStoppedError):
            self._bridge.frames(count)

    def _application_seconds(self) -> Optional[float]:
        """The application's clock, or ``None`` once a gesture has closed the application."""
        try:
            return float(self._bridge.ask(dpg.get_total_time))
        except RenderThreadStoppedError:
            return None

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

    def _on_display(self, point: Point) -> Point:
        """The display pixel at ``point`` of the viewport."""
        viewport = self._bridge.ask(read_viewport)
        return Point(x=round(viewport.x) + point.x, y=round(viewport.y) + point.y)

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
