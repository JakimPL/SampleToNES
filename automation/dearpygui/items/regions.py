from dataclasses import dataclass
from typing import List, Optional, Tuple

import dearpygui.dearpygui as dpg

from automation.dearpygui.geometry import Rect
from automation.dearpygui.items.reading import _window_rect, read_item
from automation.dearpygui.items.types import (
    CHILD_WINDOW_TYPE,
    TABLE_TYPE,
    WINDOW_TYPE,
    Item,
)
from automation.dearpygui.items.viewport import read_client_area


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
    held = item
    parent = dpg.get_item_parent(item)
    while parent is not None:
        if _clips(parent, held):
            regions.append(parent)

        held = parent
        parent = dpg.get_item_parent(parent)

    return tuple(regions)


def _clips(region: Item, held: Item) -> bool:
    """Whether ``region`` clips the child ``held`` and scrolls it: a child window, or a table scrolling that row.

    A table scrolling on its own clips the rows it scrolls, and the rows it freezes stand above
    them in view whatever the scroll. It counts as a region where the rows it freezes are rows it
    holds, since those rows say where its view begins. One drawing its own header keeps that
    height to itself, so the window around it stands as its region. Runs on the render thread.
    """
    kind = dpg.get_item_info(region)["type"]
    if kind == CHILD_WINDOW_TYPE:
        return True

    if kind != TABLE_TYPE:
        return False

    configuration = dpg.get_item_configuration(region)
    if not configuration.get("scrollY") or configuration.get("header_row"):
        return False

    frozen = int(configuration.get("freeze_rows") or 0)
    return held not in dpg.get_item_children(region, 1)[:frozen]


def read_region_view(region: Item) -> Optional[Rect]:
    """The part of ``region``'s box its content shows through, its scrollbars and far padding left out.

    Runs on the render thread. A region reports the room left for its content, which is its box
    less its padding on both sides and the scrollbars standing in it, so the view keeps the near
    side whole and gives up half of what the region withholds on the far side, which covers its
    scrollbar. A table reports no box, so its view is read off the region around it.
    """
    if dpg.get_item_info(region)["type"] == TABLE_TYPE:
        return _table_view(region)

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


def _table_view(table: Item) -> Optional[Rect]:
    """The box a table shows its scrolling rows through: the view around it, from below the rows it freezes.

    Reads ``None`` while the table, the region around it or its frozen rows report no box. Runs on
    the render thread.
    """
    around = enclosing_regions(table)
    view = read_region_view(around[0]) if around else None
    if view is None:
        return None

    top = _frozen_bottom(table, view.y)
    if top is None:
        return None

    return Rect(x=view.x, y=top, width=view.width, height=view.y + view.height - top)


def _frozen_bottom(table: Item, view_top: float) -> Optional[float]:
    """Where the rows a table freezes at its top end, or ``view_top`` while it freezes none.

    Each frozen row's height is that of the tallest item in it, so the bottom is the lowest edge
    any item in those rows reaches. Runs on the render thread.
    """
    frozen = int(dpg.get_item_configuration(table).get("freeze_rows") or 0)
    if frozen == 0:
        return view_top

    bottoms = [
        box.y + box.height
        for row in dpg.get_item_children(table, 1)[:frozen]
        for cell in dpg.get_item_children(row, 1)
        for child in dpg.get_item_children(cell, 1)
        if (box := read_item(child).rect) is not None
    ]
    return max(bottoms) if bottoms else None


def read_visible_box(item: Item) -> Optional[Rect]:
    """The part of ``item``'s box the regions around it and the viewport leave in view. Runs on the render thread."""
    box = _table_view(item) if dpg.get_item_info(item)["type"] == TABLE_TYPE else read_item(item).rect
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
