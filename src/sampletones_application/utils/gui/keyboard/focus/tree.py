from dataclasses import dataclass
from typing import Any, Dict, Final, List, Optional

import dearpygui.dearpygui as dpg

from sampletones_shared.types.application import Sender

STATE_ACTIVE: Final = "active"
STATE_FOCUSED: Final = "focused"


@dataclass(frozen=True)
class ItemNode:
    """One widget of the item tree, as the search for the edited field reads it."""

    item: Sender
    item_type: str
    children: List[Sender]


def focused_item() -> Optional[Sender]:
    """The item DearPyGui reports as holding the keyboard, or ``None`` while it reports none."""
    item: Sender = dpg.get_focused_item()
    if not item:
        return None

    return item


def item_exists(item: Sender) -> bool:
    """Whether ``item`` is still part of the item tree.

    DearPyGui keeps reporting the last focused item after the widget behind it is gone, which the
    sequencer does whenever it rebuilds its tables, so a reported item is confirmed to be live
    before anything else is read from it.
    """
    exists: bool = dpg.does_item_exist(item)
    return exists


def read_item(item: Sender) -> ItemNode:
    """Reads the type and children of ``item`` in the one DearPyGui query that carries both."""
    info: Dict[str, Any] = dpg.get_item_info(item)
    slots: Dict[int, List[Sender]] = info["children"]
    return ItemNode(
        item=item,
        item_type=info["type"],
        children=[child for children in slots.values() for child in children],
    )


def is_item_active(item: Sender) -> bool:
    """Whether DearPyGui reports ``item`` as the one the user is interacting with."""
    return _state_flag(item, STATE_ACTIVE)


def is_item_focused(item: Sender) -> bool:
    """Whether DearPyGui reports ``item`` as holding the keyboard focus."""
    return _state_flag(item, STATE_FOCUSED)


def _state_flag(item: Sender, flag: str) -> bool:
    """The value DearPyGui reports for ``flag`` in the state of ``item``.

    Item state is a per-type dictionary: the widgets that respond to interaction carry the
    interaction flags, as do the groups that lay them out, and a container such as a table row
    answers ``False`` through their absence.
    """
    state: Dict[str, Any] = dpg.get_item_state(item)
    return state.get(flag) is True
