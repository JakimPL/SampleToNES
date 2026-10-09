from dataclasses import dataclass
from typing import Any, Callable, Dict, Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from automation.dearpygui.geometry import Rect
from automation.dearpygui.items.types import (
    CHILD_WINDOW_TYPE,
    WINDOW_TYPE,
    Item,
)

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


def read_hovered(item: Item) -> Optional[bool]:
    """Whether the pointer rested on ``item`` in the last frame, or ``None`` for a kind reporting no hover.

    Runs on the render thread. An item covered by a popup, clipped by the region it scrolls in, or
    passed over while another item holds the mouse reads as not hovered.
    """
    state = dpg.get_item_state(item)
    if "hovered" not in state:
        return None

    return bool(state["hovered"])


def read_value(item: Item) -> Any:
    """The value ``item`` holds, whatever kind the item keeps. Runs on the render thread."""
    return dpg.get_value(item)


def read_selected_tab(tab_bar: str) -> str:
    """The tag of the tab standing in front of ``tab_bar``. Runs on the render thread."""
    return str(dpg.get_item_alias(dpg.get_value(tab_bar)))


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
    while parent is not None and dpg.get_item_info(parent)["type"] not in (
        WINDOW_TYPE,
        CHILD_WINDOW_TYPE,
    ):
        parent = dpg.get_item_parent(parent)

    if parent is None:
        raise LookupError(f"{item!r} stands in no window")

    return parent


def _window_rect(window: Item) -> Rect:
    return Rect.of(
        dpg.get_item_pos(window),
        dpg.get_item_state(window)["rect_size"],
    )
