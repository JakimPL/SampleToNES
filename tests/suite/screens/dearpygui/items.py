from dataclasses import dataclass
from typing import Any, Callable, Dict, Final, List, Optional, Tuple, Union

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.geometry import Point, Rect

Item = Union[int, str]

WINDOW_TYPE: Final[str] = "mvAppItemType::mvWindowAppItem"
CHILD_WINDOW_TYPE: Final[str] = "mvAppItemType::mvChildWindow"
TREE_NODE_TYPE: Final[str] = "mvAppItemType::mvTreeNode"
MENU_TYPE: Final[str] = "mvAppItemType::mvMenu"
MENU_ITEM_TYPE: Final[str] = "mvAppItemType::mvMenuItem"
TEXT_TYPE: Final[str] = "mvAppItemType::mvText"
BUTTON_TYPE: Final[str] = "mvAppItemType::mvButton"
TAG_SEPARATOR: Final[str] = "."


@dataclass(frozen=True)
class ItemReading:
    """What one item showed in the last frame: whether it stands, where, and whether it answers.

    Attributes:
        item: The item read.
        exists: Whether the item is in the context at all.
        shown: Whether the item and every container around it are shown.
        visible: Whether the item was drawn inside its clip region in the last frame.
        enabled: Whether the item and every container around it answer a press.
        rect: The item's box on the screen, where its kind reports one.
    """

    item: Item
    exists: bool
    shown: bool
    visible: bool
    enabled: bool
    rect: Optional[Rect]


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


def read_item(item: Item) -> ItemReading:
    """Reads ``item`` as the last frame drew it. Runs on the render thread."""
    if not dpg.does_item_exist(item):
        return ItemReading(
            item=item,
            exists=False,
            shown=False,
            visible=False,
            enabled=False,
            rect=None,
        )

    state = dpg.get_item_state(item)
    configuration = dpg.get_item_configuration(item)
    return ItemReading(
        item=item,
        exists=True,
        shown=_shown_with_ancestors(item),
        visible=bool(state.get("visible", True)),
        enabled=bool(configuration.get("enabled", True)) and _enabled_ancestors(item),
        rect=_rect(item, state),
    )


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


def find_item(
    container: Item,
    matches: Callable[[Item], bool],
) -> Optional[Item]:
    """The first item under ``container``, in the order they are drawn, that ``matches`` accepts.

    Runs on the render thread.
    """
    pending: List[Item] = [container]
    while pending:
        item = pending.pop(0)
        if matches(item):
            return item

        pending[:0] = [child for children in dpg.get_item_info(item)["children"].values() for child in children]

    return None


def read_item_count() -> int:
    """How many items the context holds, which grows with what the interface builds. Runs on the render thread."""
    return len(dpg.get_all_items())


@dataclass(frozen=True)
class EntryReading:
    """One entry of a popup menu: its words, where it stands in the viewport, and whether it answers."""

    label: str
    point: Point
    enabled: bool


def read_popup_entries(popup: Item) -> Tuple[EntryReading, ...]:
    """The menu entries a popup window holds, in order. Runs on the render thread.

    DearPyGui reports an entry's position inside the popup alone, so the entry stands where the
    popup does, moved by that position.
    """
    corner = dpg.get_item_pos(popup)
    entries: List[EntryReading] = []
    for child in dpg.get_item_children(popup, 1):
        if dpg.get_item_info(child)["type"] != MENU_ITEM_TYPE:
            continue

        position = dpg.get_item_state(child)["pos"]
        entries.append(
            EntryReading(
                label=read_label(child),
                point=Point(x=round(corner[0] + position[0]), y=round(corner[1] + position[1])),
                enabled=bool(dpg.get_item_configuration(child).get("enabled", True)),
            )
        )

    return tuple(entries)


def read_hovered(item: Item) -> Optional[bool]:
    """Whether the pointer rested on ``item`` in the last frame, or ``None`` for a kind reporting no hover.

    Runs on the render thread. An item covered by a popup, clipped by the region it scrolls in, or
    passed over while another item holds the mouse reads as not hovered.
    """
    state = dpg.get_item_state(item)
    if "hovered" not in state:
        return None

    return bool(state["hovered"])


def read_theme(item: Item) -> Optional[str]:
    """The tag of the theme bound to ``item``, if one is. Runs on the render thread."""
    theme = dpg.get_item_info(item)["theme"]
    if theme is None:
        return None

    return str(dpg.get_item_alias(theme))


def read_label(item: Item) -> str:
    """The label ``item`` carries. Runs on the render thread."""
    return str(dpg.get_item_label(item) or "")


def read_value(item: Item) -> Any:
    """The value ``item`` holds, whatever kind the item keeps. Runs on the render thread."""
    return dpg.get_value(item)


def read_shown_texts(container: Item) -> Tuple[str, ...]:
    """The words of every shown text item under ``container``, in the order they are drawn.

    Runs on the render thread.
    """
    return _texts(container, shown_only=True)


def read_texts(container: Item) -> Tuple[str, ...]:
    """The words of every text item under ``container``, shown or waiting to be, such as a tooltip's.

    Runs on the render thread.
    """
    return _texts(container, shown_only=False)


def read_theme_colors(theme: Item) -> Tuple[Tuple[float, ...], ...]:
    """The colors every theme color under ``theme`` holds, in the order they were added. Runs on the render thread."""
    colors: List[Tuple[float, ...]] = []
    for component in dpg.get_item_children(theme, 1):
        for color in dpg.get_item_children(component, 1):
            colors.append(tuple(float(part) for part in dpg.get_value(color)))

    return tuple(colors)


def read_visible_text(words: str) -> bool:
    """Whether a text item reading ``words`` was drawn in the last frame, such as a tooltip standing open.

    Runs on the render thread.
    """
    return any(
        dpg.get_item_info(item)["type"] == TEXT_TYPE
        and dpg.get_value(item) == words
        and bool(dpg.is_item_visible(item))
        for item in dpg.get_all_items()
    )


def read_shown_labels(container: Item, item_type: str) -> Tuple[str, ...]:
    """The labels of every shown item of ``item_type`` under ``container``, in the order they are drawn.

    Runs on the render thread.
    """
    labels: List[str] = []
    pending: List[Item] = [container]
    while pending:
        item = pending.pop(0)
        if not dpg.is_item_shown(item):
            continue

        info = dpg.get_item_info(item)
        if info["type"] == item_type:
            labels.append(read_label(item))

        pending[:0] = [child for children in info["children"].values() for child in children]

    return tuple(labels)


def _texts(container: Item, *, shown_only: bool) -> Tuple[str, ...]:
    texts: List[str] = []
    pending: List[Item] = [container]
    while pending:
        item = pending.pop(0)
        if shown_only and not dpg.is_item_shown(item):
            continue

        info = dpg.get_item_info(item)
        if info["type"] == TEXT_TYPE:
            texts.append(str(dpg.get_value(item)))

        pending[:0] = [child for children in info["children"].values() for child in children]

    return tuple(texts)


def find_labelled(
    container: Item,
    label: str,
    *,
    item_type: str,
) -> Item:
    """The first item of ``item_type`` under ``container`` whose label reads ``label``. Runs on the render thread.

    A label may carry padding around its words, so the words are compared with the padding stripped.

    Raises:
        LookupError: If no such item stands under ``container``.
    """
    pending: List[Item] = [container]
    while pending:
        item = pending.pop(0)
        info = dpg.get_item_info(item)
        if info["type"] == item_type and read_label(item).strip() == label.strip():
            return item

        for children in info["children"].values():
            pending.extend(children)

    raise LookupError(f"No {item_type} labelled '{label}' stands under {container!r}")


def read_selected_tab(tab_bar: str) -> str:
    """The tag of the tab standing in front of ``tab_bar``. Runs on the render thread."""
    return str(dpg.get_item_alias(dpg.get_value(tab_bar)))


def read_viewport() -> Rect:
    """The viewport's client area, placed where it stands on the screen. Runs on the render thread."""
    corner = dpg.get_viewport_pos()
    return Rect(
        x=corner[0],
        y=corner[1],
        width=dpg.get_viewport_client_width(),
        height=dpg.get_viewport_client_height(),
    )


def read_viewport_title() -> str:
    """The title the viewport's window carries in its title bar. Runs on the render thread."""
    return str(dpg.get_viewport_title())


def read_pointer() -> Point:
    """Where the pointer stands in the viewport, as the application last saw it. Runs on the render thread."""
    position = dpg.get_mouse_pos(local=False)
    return Point(x=round(position[0]), y=round(position[1]))


def read_client_area() -> Rect:
    """The viewport's client area in the coordinates its items report. Runs on the render thread."""
    return Rect(
        x=0,
        y=0,
        width=dpg.get_viewport_client_width(),
        height=dpg.get_viewport_client_height(),
    )


def is_tag_within(alias: str, prefix: str) -> bool:
    """Whether ``alias`` is ``prefix`` itself or a tag composed under it."""
    return alias == prefix or alias.startswith(prefix + TAG_SEPARATOR)


def _shown_with_ancestors(tag: Item) -> bool:
    item: Optional[Item] = tag
    while item is not None:
        if not dpg.is_item_shown(item):
            return False

        item = dpg.get_item_parent(item)

    return True


def _enabled_ancestors(tag: Item) -> bool:
    parent = dpg.get_item_parent(tag)
    while parent is not None:
        if not dpg.get_item_configuration(parent).get("enabled", True):
            return False

        parent = dpg.get_item_parent(parent)

    return True


def _rect(item: Item, state: Dict[str, Any]) -> Optional[Rect]:
    if "rect_min" in state:
        return Rect.of(state["rect_min"], state["rect_size"])

    item_type = dpg.get_item_info(item)["type"]
    if item_type == WINDOW_TYPE:
        return _window_rect(item)
    if item_type == CHILD_WINDOW_TYPE:
        return Rect.of(_child_window_corner(item), state["rect_size"])

    return None


def _child_window_corner(child: Item) -> Tuple[float, float]:
    """Where a child window stands on the screen.

    DearPyGui reports a child window's position in the content of the window holding it, which
    scrolls, so the corner is that window's own corner moved by the position and back by the scroll.
    """
    container = _containing_window(child)
    if dpg.get_item_info(container)["type"] == WINDOW_TYPE:
        corner = dpg.get_item_pos(container)
    else:
        corner = _child_window_corner(container)

    position = dpg.get_item_state(child)["pos"]
    return (
        corner[0] + position[0] - dpg.get_x_scroll(container),
        corner[1] + position[1] - dpg.get_y_scroll(container),
    )


def _containing_window(item: Item) -> Item:
    parent: Optional[Item] = dpg.get_item_parent(item)
    while parent is not None and dpg.get_item_info(parent)["type"] not in (WINDOW_TYPE, CHILD_WINDOW_TYPE):
        parent = dpg.get_item_parent(parent)

    if parent is None:
        raise LookupError(f"{item!r} stands in no window")

    return parent


def _window_rect(window: Item) -> Rect:
    return Rect.of(
        dpg.get_item_pos(window),
        dpg.get_item_state(window)["rect_size"],
    )
