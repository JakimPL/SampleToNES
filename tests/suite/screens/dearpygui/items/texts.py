from dataclasses import dataclass
from typing import List, Tuple

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.items.types import MENU_ITEM_TYPE, TEXT_TYPE, Item


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


def read_label(item: Item) -> str:
    """The label ``item`` carries. Runs on the render thread."""
    return str(dpg.get_item_label(item) or "")


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
