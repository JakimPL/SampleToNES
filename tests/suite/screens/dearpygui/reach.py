from typing import Optional

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.geometry import Rect
from tests.suite.screens.dearpygui.items.reading import ItemReading, read_item
from tests.suite.screens.dearpygui.items.regions import read_visible_box, read_windows
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.dearpygui.items.viewport import read_client_area


class UnreachableError(AssertionError):
    """Raised when a scenario reaches for a control a user could not press."""


def reachable(item: Item) -> Rect:
    """The box of ``item``, once it stands where a user could press it. Runs on the render thread.

    A control is in reach when it exists, it and every container around it are shown, it was drawn
    in the last frame, it answers a press, its box lies inside the viewport, its middle lies in the
    part the regions around it leave in view, and no modal window of another tree holds the screen.

    Raises:
        UnreachableError: Naming the first condition the control misses.
    """
    reading = read_item(item)
    refusal = _refusal(reading)
    if refusal is not None:
        raise UnreachableError(f"{item!r} is out of reach: {refusal}")

    assert reading.rect is not None
    return reading.rect


def _refusal(reading: ItemReading) -> Optional[str]:
    if not reading.exists:
        return "it does not exist"
    if not reading.shown:
        return "it or a container around it is hidden"
    if not reading.visible:
        return "it was not drawn in the last frame"
    if not reading.enabled:
        return "it is disabled"
    if reading.rect is None:
        return "its kind reports no box to press"
    if not read_client_area().contains(reading.rect):
        return f"its box {reading.rect} reaches outside the viewport"

    visible = read_visible_box(reading.item)
    if visible is None or not visible.holds(reading.rect.center):
        return "its middle lies outside the part the regions around it leave in view"

    covering = covering_modal(reading.item)
    if covering is not None:
        return f"the modal window '{covering}' holds the screen"

    return None


def covering_modal(item: Item) -> Optional[str]:
    """The modal window of another tree holding the screen over ``item``, if one does."""
    root = _root_window(item)
    for window in read_windows():
        if window.shown and window.modal and window.alias != root:
            return window.alias

    return None


def _root_window(item: Item) -> str:
    root: Item = item
    parent = dpg.get_item_parent(root)
    while parent is not None:
        root = parent
        parent = dpg.get_item_parent(root)

    return str(dpg.get_item_alias(root))
