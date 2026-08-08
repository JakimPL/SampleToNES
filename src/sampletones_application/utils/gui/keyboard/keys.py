from typing import Dict, Final, FrozenSet

import dearpygui.dearpygui as dpg

from sampletones_shared.constants.symbols import HEXADECIMAL, MINUS, PLUS

KEY_PAGE_UP: Final[int] = 517
KEY_PAGE_DOWN: Final[int] = 518

UNKNOWN_KEY: Final[str] = "?"

LETTER_COUNT: Final[int] = 26
DIGIT_COUNT: Final[int] = 10
FUNCTION_KEY_COUNT: Final[int] = 12

LETTER_NAMES: Final[Dict[int, str]] = {dpg.mvKey_A + offset: chr(ord("A") + offset) for offset in range(LETTER_COUNT)}
DIGIT_NAMES: Final[Dict[int, str]] = {dpg.mvKey_0 + offset: str(offset) for offset in range(DIGIT_COUNT)}
FUNCTION_KEY_NAMES: Final[Dict[int, str]] = {
    dpg.mvKey_F1 + offset: f"F{offset + 1}" for offset in range(FUNCTION_KEY_COUNT)
}

FUNCTION_KEYS: Final[FrozenSet[int]] = frozenset(FUNCTION_KEY_NAMES)

KEY_DISPLAY_NAMES: Final[Dict[int, str]] = {
    **LETTER_NAMES,
    **DIGIT_NAMES,
    **FUNCTION_KEY_NAMES,
    dpg.mvKey_Escape: "Esc",
    dpg.mvKey_Return: "Enter",
    dpg.mvKey_Tab: "Tab",
    dpg.mvKey_Spacebar: "Space",
    dpg.mvKey_Back: "Backspace",
    dpg.mvKey_Delete: "Del",
    dpg.mvKey_Insert: "Ins",
    dpg.mvKey_Home: "Home",
    dpg.mvKey_End: "End",
    KEY_PAGE_UP: "PgUp",
    KEY_PAGE_DOWN: "PgDn",
    dpg.mvKey_Up: "Up",
    dpg.mvKey_Down: "Down",
    dpg.mvKey_Left: "Left",
    dpg.mvKey_Right: "Right",
    dpg.mvKey_Plus: PLUS,
    dpg.mvKey_Minus: MINUS,
    dpg.mvKey_Add: f"Num{PLUS}",
    dpg.mvKey_Subtract: f"Num{MINUS}",
}

KEY_CODES: Final[Dict[str, int]] = {name.casefold(): key for key, name in KEY_DISPLAY_NAMES.items()}


HEX_KEYS: Final[Dict[int, str]] = {dpg.mvKey_0 + offset: HEXADECIMAL[offset] for offset in range(DIGIT_COUNT)} | {
    dpg.mvKey_A + offset: HEXADECIMAL[DIGIT_COUNT + offset] for offset in range(len(HEXADECIMAL) - DIGIT_COUNT)
}

SIGN_KEYS: Final[Dict[int, str]] = {
    dpg.mvKey_Minus: MINUS,
    dpg.mvKey_Subtract: MINUS,
    dpg.mvKey_Plus: PLUS,
    dpg.mvKey_Add: PLUS,
}


def key_display(key: int) -> str:
    """The name a key reads under, falling back to a placeholder for a key the table omits.

    Args:
        key: The key code a press carries.

    Returns:
        str: The name the key shows wherever a combination is displayed.
    """
    return KEY_DISPLAY_NAMES.get(key, UNKNOWN_KEY)


def key_code(name: str) -> int:
    """The key a written name stands for, however the name is capitalised.

    Reading a name back into a code is what lets a binding be written down, so a configured
    combination and a declared one arrive at the same key.

    Args:
        name: A key name as :func:`key_display` writes it.

    Returns:
        int: The key code the name stands for.

    Raises:
        KeyError: If the table holds no key under that name.
    """
    key = KEY_CODES.get(name.casefold())
    if key is None:
        raise KeyError(f"No key carries the name {name!r}")

    return key
