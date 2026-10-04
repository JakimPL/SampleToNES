from typing import Dict, Final, FrozenSet

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind
from sampletones_application.utils.gui.keyboard.keys import CHARACTER_KEYS, FUNCTION_KEYS
from sampletones_application.utils.gui.keyboard.modifiers import (
    CTRL,
    CTRL_SHIFT,
    SUPER,
    SUPER_SHIFT,
    Modifier,
    ModifierSet,
)

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

TEXT_EDIT_KEYS: Final[FrozenSet[int]] = frozenset(
    {
        dpg.mvKey_A,
        dpg.mvKey_C,
        dpg.mvKey_V,
        dpg.mvKey_X,
        dpg.mvKey_Z,
        dpg.mvKey_Y,
    }
)
REDO_KEYS: Final[FrozenSet[int]] = frozenset({dpg.mvKey_Z})

TEXT_EDIT_CHORDS: Final[Dict[ModifierSet, FrozenSet[int]]] = {
    CTRL: TEXT_EDIT_KEYS,
    CTRL_SHIFT: REDO_KEYS,
    SUPER: TEXT_EDIT_KEYS,
    SUPER_SHIFT: REDO_KEYS,
}


def field_consumes_key(kind: FieldKind, key: int, modifiers: ModifierSet) -> bool:
    """Whether a focused field of ``kind`` acts on this key, so a matching shortcut yields to it.

    A field keeps the keys it uses and lets the rest reach the shortcut. Plain characters and the
    caret, commit, and cancel keys belong to whichever field is focused.

    A command chord, one held with Ctrl or Super, reaches the shortcuts, so Ctrl+Space plays and
    Cmd+S saves from a field. A field that types keeps the text-edit chords alone: select all,
    copy, cut, paste, undo and redo, spelled with Ctrl and with Super, the key macOS spells them
    with. Super decides first, so Cmd+Option+S is a command as well.

    A text-entry field also keeps an Alt chord on a key that types a character, because AltGr and
    Option type characters that way: Linux reports AltGr as Alt and Windows as Ctrl+Alt. An Alt
    chord on a function, caret or editing key reaches the shortcuts, so Alt+F4 stays reachable
    while a field is focused. A number field types no such character, so every Alt chord reaches
    the shortcuts from it.
    """
    if kind is FieldKind.NONE:
        return False

    if Modifier.SUPER in modifiers:
        return _keeps_text_edit_chord(kind, key, modifiers)

    if Modifier.ALT in modifiers:
        return kind is FieldKind.TEXT_ENTRY and key in CHARACTER_KEYS

    if Modifier.CTRL in modifiers:
        return _keeps_text_edit_chord(kind, key, modifiers)

    if key in EDITING_KEYS:
        return True

    return kind.takes_typing and key not in FUNCTION_KEYS


def _keeps_text_edit_chord(kind: FieldKind, key: int, modifiers: ModifierSet) -> bool:
    return kind.takes_typing and key in TEXT_EDIT_CHORDS.get(
        modifiers,
        NO_KEYS,
    )
