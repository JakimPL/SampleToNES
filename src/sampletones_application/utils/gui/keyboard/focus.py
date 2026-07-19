from typing import Final, FrozenSet

import dearpygui.dearpygui as dpg

FIELD_ITEM_TYPES: Final[FrozenSet[str]] = frozenset(
    {
        "mvAppItemType::mvInputText",
        "mvAppItemType::mvInputInt",
        "mvAppItemType::mvInputFloat",
        "mvAppItemType::mvInputDouble",
        "mvAppItemType::mvCombo",
        "mvAppItemType::mvSliderInt",
        "mvAppItemType::mvSliderFloat",
        "mvAppItemType::mvDragInt",
        "mvAppItemType::mvDragFloat",
    }
)


def is_field_focused() -> bool:
    """Whether the keyboard is editing a text or value field right now.

    The focused item is read straight from DearPyGui on each key press and counts only while it
    is a field type that is actively being edited, so every input the user types into keeps plain
    keys away from shortcuts and the tracker tables on its own, with no per-input wiring. Reading
    focus at the source also closes the gap where an input that skipped registration let shortcuts
    fire mid-edit.
    """
    item = dpg.get_focused_item()
    if not item:
        return False

    if dpg.get_item_type(item) not in FIELD_ITEM_TYPES:
        return False

    return bool(dpg.is_item_active(item))
