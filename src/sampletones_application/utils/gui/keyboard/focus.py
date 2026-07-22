from enum import Enum
from typing import Final, FrozenSet

import dearpygui.dearpygui as dpg


class FieldKind(Enum):
    """What a focused widget does with a key press, which decides the keys it keeps for itself.

    ``TEXT_ENTRY`` inserts typed characters (text and number inputs); ``CHOICE`` navigates a list
    of options (an open combo); ``NONE`` is any other focus, which yields every key.
    """

    NONE = "none"
    TEXT_ENTRY = "text_entry"
    CHOICE = "choice"


TEXT_ENTRY_ITEM_TYPES: Final[FrozenSet[str]] = frozenset(
    {
        "mvAppItemType::mvInputText",
        "mvAppItemType::mvInputInt",
        "mvAppItemType::mvInputFloat",
        "mvAppItemType::mvInputDouble",
        "mvAppItemType::mvSliderInt",
        "mvAppItemType::mvSliderFloat",
        "mvAppItemType::mvDragInt",
        "mvAppItemType::mvDragFloat",
    }
)

CHOICE_ITEM_TYPES: Final[FrozenSet[str]] = frozenset({"mvAppItemType::mvCombo"})

EDITING_KEYS: Final[FrozenSet[int]] = frozenset(
    {
        dpg.mvKey_Escape,
        dpg.mvKey_Return,
        dpg.mvKey_Tab,
        dpg.mvKey_Back,
        dpg.mvKey_Delete,
        dpg.mvKey_Insert,
        dpg.mvKey_Home,
        dpg.mvKey_End,
        dpg.mvKey_Left,
        dpg.mvKey_Right,
        dpg.mvKey_Up,
        dpg.mvKey_Down,
    }
)

TEXT_EDIT_CHORDS: Final[FrozenSet[int]] = frozenset(
    {
        dpg.mvKey_A,
        dpg.mvKey_C,
        dpg.mvKey_V,
        dpg.mvKey_X,
        dpg.mvKey_Z,
        dpg.mvKey_Y,
    }
)

FUNCTION_KEYS: Final[FrozenSet[int]] = frozenset(
    {
        dpg.mvKey_F1,
        dpg.mvKey_F2,
        dpg.mvKey_F3,
        dpg.mvKey_F4,
        dpg.mvKey_F5,
        dpg.mvKey_F6,
        dpg.mvKey_F7,
        dpg.mvKey_F8,
        dpg.mvKey_F9,
        dpg.mvKey_F10,
        dpg.mvKey_F11,
        dpg.mvKey_F12,
    }
)


def focused_field_kind() -> FieldKind:
    """The kind of field editing the keyboard right now, or ``NONE`` when none is.

    The focused item is read straight from DearPyGui on each key press and counts only while it is
    a field type that is actively being edited, so every input the user types into keeps its keys
    on its own. A combo counts only while its popup is open, when it owns the arrows and Escape.

    DearPyGui keeps reporting the last focused item after the widget behind it is gone, which the
    sequencer does whenever it rebuilds its tables, so the item is confirmed to still exist before
    it is queried and a vanished field counts as no field focused. The item type is checked before
    its active state because only field types report an ``active`` flag; other focused widgets, such
    as a selectable or a table, carry no such state to read.
    """
    item = dpg.get_focused_item()
    if not item:
        return FieldKind.NONE

    if not dpg.does_item_exist(item):
        return FieldKind.NONE

    item_type = dpg.get_item_type(item)
    if item_type in TEXT_ENTRY_ITEM_TYPES:
        kind = FieldKind.TEXT_ENTRY
    elif item_type in CHOICE_ITEM_TYPES:
        kind = FieldKind.CHOICE
    else:
        return FieldKind.NONE

    if not dpg.is_item_active(item):
        return FieldKind.NONE

    return kind


def is_field_focused() -> bool:
    """Whether any field is editing the keyboard, so plain keys stay with it.

    The scopes consult this single flag, so a key press stays with the field the user is typing
    into and reaches the panels and shortcuts otherwise.
    """
    return focused_field_kind() is not FieldKind.NONE


def field_consumes_key(
    kind: FieldKind,
    key: int,
    *,
    ctrl: bool,
    shift: bool,
    alt: bool,
) -> bool:
    """Whether a focused field of ``kind`` acts on this key, so a matching shortcut yields to it.

    A field keeps the keys it uses and lets the rest reach the shortcut. Plain characters and the
    caret, commit, and cancel keys belong to whichever field is focused; a text-entry field also
    keeps the select, undo, and clipboard Ctrl-chords. Every other combination passes through:
    command chords such as Ctrl+Space, Alt shortcuts, and the function keys, so intentional
    playback and Stop stay reachable while a field is focused.
    """
    if kind is FieldKind.NONE:
        return False

    if alt:
        return False

    if ctrl:
        return kind is FieldKind.TEXT_ENTRY and key in TEXT_EDIT_CHORDS

    if key in EDITING_KEYS:
        return True

    return kind is FieldKind.TEXT_ENTRY and key not in FUNCTION_KEYS
