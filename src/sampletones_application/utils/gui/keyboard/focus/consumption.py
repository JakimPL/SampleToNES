from typing import Final, FrozenSet

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind

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
