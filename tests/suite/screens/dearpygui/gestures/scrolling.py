from functools import partial
from typing import Final

from tests.suite.screens.dearpygui.bridge import ONE_FRAME
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.gestures.constants import HOVER_FRAMES, SETTLE_FRAMES
from tests.suite.screens.dearpygui.gestures.pointer import Pointer
from tests.suite.screens.dearpygui.items.reading import read_item
from tests.suite.screens.dearpygui.items.regions import (
    enclosing_regions,
    read_region_view,
    read_scroll,
    read_visible_box,
)
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.dearpygui.items.viewport import read_viewport
from tests.suite.screens.dearpygui.reach import UnreachableError
from tests.suite.screens.dearpygui.xtest import MouseButton

WHEEL_FRAMES: Final[int] = 1
SCROLL_NOTCH_LIMIT: Final[int] = 100
EDGE_INSET: Final[int] = 3
GRIP_MARGIN_PIXELS: Final[float] = 8.0
GRIP_DRAGS: Final[int] = 4
IMGUI_GRAB_MIN_SIZE: Final[float] = 12.0


class Scrolling(Pointer):
    """The wheel and the scrollbars of a hand: turning the wheel over a region and bringing an item into view.

    It owns every gesture that moves a region's scroll. It rests the pointer with `Pointer`'s hover,
    turns the wheel through the display's input device, and drags a scrollbar grip with `Pointer`'s drag
    where the wheel leaves the region alone.
    """

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

    def _turn_wheel(self, notches: int) -> None:
        button = MouseButton.WHEEL_DOWN if notches > 0 else MouseButton.WHEEL_UP
        for _ in range(abs(notches)):
            self._device.button_down(button)
            self._settle(WHEEL_FRAMES)
            self._device.button_up(button)
            self._settle(WHEEL_FRAMES)


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
