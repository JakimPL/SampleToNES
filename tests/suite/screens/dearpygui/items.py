from dataclasses import dataclass
from typing import Any, Dict, Final, List, Optional, Tuple, Union

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.geometry import Rect

Item = Union[int, str]

WINDOW_TYPE: Final[str] = "mvAppItemType::mvWindowAppItem"
MENU_TYPE: Final[str] = "mvAppItemType::mvMenu"
MENU_ITEM_TYPE: Final[str] = "mvAppItemType::mvMenuItem"
TAG_SEPARATOR: Final[str] = "."


@dataclass(frozen=True)
class ItemReading:
    """What one item showed in the last frame: whether it stands, where, and whether it answers.

    Attributes:
        item: The item read.
        exists: Whether the item is in the context at all.
        shown: Whether the item and every container around it are shown.
        visible: Whether the item was drawn inside its clip region in the last frame.
        enabled: Whether the item answers a press.
        rect: The item's box on the screen, where its kind reports one.
    """

    item: Item
    exists: bool
    shown: bool
    visible: bool
    enabled: bool
    rect: Optional[Rect]


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
        enabled=bool(configuration.get("enabled", True)),
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


def read_hovered(item: Item) -> Optional[bool]:
    """Whether the pointer rested on ``item`` in the last frame, or ``None`` for a kind reporting no hover.

    Runs on the render thread. An item covered by a popup, clipped by the region it scrolls in, or
    passed over while another item holds the mouse reads as not hovered.
    """
    state = dpg.get_item_state(item)
    if "hovered" not in state:
        return None

    return bool(state["hovered"])


def read_label(item: Item) -> str:
    """The label ``item`` carries. Runs on the render thread."""
    return str(dpg.get_item_label(item) or "")


def read_value(item: Item) -> Any:
    """The value ``item`` holds, whatever kind the item keeps. Runs on the render thread."""
    return dpg.get_value(item)


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


def _rect(item: Item, state: Dict[str, Any]) -> Optional[Rect]:
    if "rect_min" in state:
        return Rect.of(state["rect_min"], state["rect_size"])

    if dpg.get_item_info(item)["type"] == WINDOW_TYPE:
        return _window_rect(item)

    return None


def _window_rect(window: Item) -> Rect:
    return Rect.of(
        dpg.get_item_pos(window),
        dpg.get_item_state(window)["rect_size"],
    )
