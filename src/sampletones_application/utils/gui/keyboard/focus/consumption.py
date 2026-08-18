from typing import Dict, Final, FrozenSet

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind
from sampletones_application.utils.gui.keyboard.keys import FUNCTION_KEYS
from sampletones_application.utils.gui.keyboard.modifiers import Modifier, ModifierSet

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

NO_KEYS: Final[FrozenSet[int]] = frozenset()

TEXT_EDIT_CHORDS: Final[Dict[ModifierSet, FrozenSet[int]]] = {
    frozenset({Modifier.CTRL}): frozenset(
        {
            dpg.mvKey_A,
            dpg.mvKey_C,
            dpg.mvKey_V,
            dpg.mvKey_X,
            dpg.mvKey_Z,
            dpg.mvKey_Y,
        }
    ),
    frozenset({Modifier.CTRL, Modifier.SHIFT}): frozenset({dpg.mvKey_Z}),
}


def field_consumes_key(kind: FieldKind, key: int, modifiers: ModifierSet) -> bool:
    """Whether a focused field of ``kind`` acts on this key, so a matching shortcut yields to it.

    A field keeps the keys it uses and lets the rest reach the shortcut. Plain characters and the
    caret, commit, and cancel keys belong to whichever field is focused; a text-entry field also
    keeps the chords the modifiers name it, so Ctrl+Z undoes and Ctrl+Shift+Z redoes the text.
    Every other combination passes through: command chords such as Ctrl+Space, the Ctrl+Shift
    combinations a text field has no use for, Alt shortcuts, and the function keys, so intentional
    playback and Stop stay reachable while a field is focused.
    """
    if kind is FieldKind.NONE:
        return False

    if Modifier.ALT in modifiers:
        return False

    if Modifier.CTRL in modifiers:
        return kind is FieldKind.TEXT_ENTRY and key in TEXT_EDIT_CHORDS.get(
            modifiers,
            NO_KEYS,
        )

    if key in EDITING_KEYS:
        return True

    return kind is FieldKind.TEXT_ENTRY and key not in FUNCTION_KEYS
