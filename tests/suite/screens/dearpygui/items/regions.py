from dataclasses import dataclass
from typing import List, Optional, Tuple

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.geometry import Rect
from tests.suite.screens.dearpygui.items.reading import _window_rect, read_item
from tests.suite.screens.dearpygui.items.types import CHILD_WINDOW_TYPE, WINDOW_TYPE, Item
from tests.suite.screens.dearpygui.items.viewport import read_client_area


@dataclass(frozen=True)
class ScrollReading:
    """How far a region that scrolls stands from its top, how far it can go, in pixels, and what moves it.

    Attributes:
        position: How far the region is scrolled down.
        maximum: How far the region can scroll down.
        by_wheel: Whether the wheel scrolls the region, or its scrollbar alone does.
    """

    position: float
    maximum: float
    by_wheel: bool


@dataclass(frozen=True)
class WindowReading:
    """One top-level window as the last frame drew it.

    Attributes:
        alias: The window's tag.
        label: The title the window carries.
        modal: Whether the window holds the screen while it stands.
        shown: Whether the window is shown.
        rect: The window's box on the screen.
    """

    alias: str
    label: str
    modal: bool
    shown: bool
    rect: Rect


def read_windows() -> Tuple[WindowReading, ...]:
    """Reads every top-level window the context holds. Runs on the render thread."""
    windows = []
    for window in dpg.get_windows():
        if dpg.get_item_info(window)["type"] != WINDOW_TYPE:
            continue

        configuration = dpg.get_item_configuration(window)
        windows.append(
            WindowReading(
                alias=str(dpg.get_item_alias(window)),
                label=str(configuration.get("label") or ""),
                modal=bool(configuration.get("modal")),
                shown=bool(dpg.is_item_shown(window)),
                rect=_window_rect(window),
            )
        )

    return tuple(windows)


def read_scroll(region: Item) -> ScrollReading:
    """How far ``region`` is scrolled down. Runs on the render thread."""
    return ScrollReading(
        position=dpg.get_y_scroll(region),
        maximum=dpg.get_y_scroll_max(region),
        by_wheel=not dpg.get_item_configuration(region).get("no_scroll_with_mouse", False),
    )


def enclosing_regions(item: Item) -> Tuple[Item, ...]:
    """The regions around ``item`` that clip what they hold, the nearest first. Runs on the render thread."""
    regions: List[Item] = []
    parent = dpg.get_item_parent(item)
    while parent is not None:
        if dpg.get_item_info(parent)["type"] == CHILD_WINDOW_TYPE:
            regions.append(parent)

        parent = dpg.get_item_parent(parent)

    return tuple(regions)


def read_region_view(region: Item) -> Optional[Rect]:
    """The part of ``region``'s box its content shows through, its scrollbars and far padding left out.

    Runs on the render thread. A region reports the room left for its content, which is its box
    less its padding on both sides and the scrollbars standing in it, so the view keeps the near
    side whole and gives up half of what the region withholds on the far side, which covers its
    scrollbar.
    """
    box = read_item(region).rect
    if box is None:
        return None

    room = dpg.get_item_state(region)["content_region_avail"]
    return Rect(
        x=box.x,
        y=box.y,
        width=box.width - (box.width - room[0]) / 2,
        height=box.height - (box.height - room[1]) / 2,
    )


def read_visible_box(item: Item) -> Optional[Rect]:
    """The part of ``item``'s box the regions around it and the viewport leave in view. Runs on the render thread."""
    box = read_item(item).rect
    for region in enclosing_regions(item):
        view = read_region_view(region)
        if box is None or view is None:
            return None

        box = box.overlap(view)

    return box.overlap(read_client_area()) if box is not None else None


def read_table(table: Item) -> Tuple[Tuple[Tuple[Item, ...], ...], ...]:
    """The items inside each cell of each row of ``table``, row by row. Runs on the render thread.

    A table keeps its columns in one slot of children and its rows in another, and each row holds
    one cell per column, whatever item the cell carries.
    """
    rows = dpg.get_item_info(table)["children"][1]
    return tuple(
        tuple(tuple(dpg.get_item_info(cell)["children"][1]) for cell in dpg.get_item_info(row)["children"][1])
        for row in rows
    )
