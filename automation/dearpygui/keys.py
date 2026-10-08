from typing import Dict, Final

from Xlib import XK

IMGUI_TAB: Final[int] = 512
IMGUI_LEFT: Final[int] = 513
IMGUI_RIGHT: Final[int] = 514
IMGUI_UP: Final[int] = 515
IMGUI_DOWN: Final[int] = 516
IMGUI_PAGE_UP: Final[int] = 517
IMGUI_PAGE_DOWN: Final[int] = 518
IMGUI_HOME: Final[int] = 519
IMGUI_END: Final[int] = 520
IMGUI_INSERT: Final[int] = 521
IMGUI_DELETE: Final[int] = 522
IMGUI_BACKSPACE: Final[int] = 523
IMGUI_SPACE: Final[int] = 524
IMGUI_ENTER: Final[int] = 525
IMGUI_ESCAPE: Final[int] = 526
IMGUI_LEFT_CTRL: Final[int] = 527
IMGUI_LEFT_SHIFT: Final[int] = 528
IMGUI_LEFT_ALT: Final[int] = 529
IMGUI_DIGIT_ZERO: Final[int] = 536
IMGUI_LETTER_A: Final[int] = 546
IMGUI_F1: Final[int] = 572
DIGIT_COUNT: Final[int] = 10
LETTER_COUNT: Final[int] = 26
FUNCTION_KEY_COUNT: Final[int] = 12

NAMED_KEYSYMS: Final[Dict[int, str]] = {
    IMGUI_TAB: "Tab",
    IMGUI_LEFT: "Left",
    IMGUI_RIGHT: "Right",
    IMGUI_UP: "Up",
    IMGUI_DOWN: "Down",
    IMGUI_PAGE_UP: "Prior",
    IMGUI_PAGE_DOWN: "Next",
    IMGUI_HOME: "Home",
    IMGUI_END: "End",
    IMGUI_INSERT: "Insert",
    IMGUI_DELETE: "Delete",
    IMGUI_BACKSPACE: "BackSpace",
    IMGUI_SPACE: "space",
    IMGUI_ENTER: "Return",
    IMGUI_ESCAPE: "Escape",
    IMGUI_LEFT_CTRL: "Control_L",
    IMGUI_LEFT_SHIFT: "Shift_L",
    IMGUI_LEFT_ALT: "Alt_L",
}

DIGIT_KEYSYMS: Final[Dict[int, str]] = {IMGUI_DIGIT_ZERO + offset: str(offset) for offset in range(DIGIT_COUNT)}

LETTER_KEYSYMS: Final[Dict[int, str]] = {
    IMGUI_LETTER_A + offset: chr(ord("a") + offset) for offset in range(LETTER_COUNT)
}

FUNCTION_KEYSYMS: Final[Dict[int, str]] = {IMGUI_F1 + offset: f"F{offset + 1}" for offset in range(FUNCTION_KEY_COUNT)}

KEYSYM_NAMES: Final[Dict[int, str]] = {
    **NAMED_KEYSYMS,
    **DIGIT_KEYSYMS,
    **LETTER_KEYSYMS,
    **FUNCTION_KEYSYMS,
}


class UnmappedKeyError(LookupError):
    """Raised when a scenario presses a key the X keyboard table holds no name for."""


def keysym_of(key: int) -> int:
    """The X keysym a press of the Dear ImGui key ``key`` arrives as.

    Dear ImGui numbers its keys in an enumeration of its own, and DearPyGui reports a press under
    that number. A few of DearPyGui's own ``mvKey_*`` constants carry older values, which is why the
    table names the enumeration's numbers.

    Raises:
        UnmappedKeyError: If the table holds no name for ``key``.
    """
    name = KEYSYM_NAMES.get(key)
    if name is None:
        raise UnmappedKeyError(f"The X keyboard table holds no name for the Dear ImGui key {key}")

    return XK.string_to_keysym(name)


def key_name(key: int) -> str:
    """The name the X keyboard table gives the Dear ImGui key ``key``, for a report a person reads."""
    return KEYSYM_NAMES.get(key, str(key))


def keysym_of_character(character: str) -> int:
    """The X keysym typing ``character`` sends; a printable ASCII keysym is its own code point."""
    return ord(character)
