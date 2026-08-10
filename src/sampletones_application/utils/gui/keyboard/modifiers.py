from enum import StrEnum
from typing import Dict, Final, FrozenSet, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.keyboard.keys import (
    KEY_LEFT_SUPER,
    KEY_MODIFIER_ALT,
    KEY_MODIFIER_CTRL,
    KEY_MODIFIER_SHIFT,
    KEY_MODIFIER_SUPER,
    KEY_RIGHT_SUPER,
)
from sampletones_shared.utils.system.system import System


class Modifier(StrEnum):
    """A modifier key a press carries, declared in the order a combination displays them."""

    SUPER = "Super"
    CTRL = "Ctrl"
    ALT = "Alt"
    SHIFT = "Shift"


ModifierSet = FrozenSet[Modifier]

NO_MODIFIERS: Final[ModifierSet] = frozenset()
CTRL: Final[ModifierSet] = frozenset({Modifier.CTRL})
ALT: Final[ModifierSet] = frozenset({Modifier.ALT})
SHIFT: Final[ModifierSet] = frozenset({Modifier.SHIFT})
SUPER: Final[ModifierSet] = frozenset({Modifier.SUPER})
CTRL_ALT: Final[ModifierSet] = frozenset({Modifier.CTRL, Modifier.ALT})
CTRL_SHIFT: Final[ModifierSet] = frozenset({Modifier.CTRL, Modifier.SHIFT})
CTRL_ALT_SHIFT: Final[ModifierSet] = frozenset({Modifier.CTRL, Modifier.ALT, Modifier.SHIFT})

MODIFIER_NAMES: Final[Dict[str, Modifier]] = {
    "ctrl": Modifier.CTRL,
    "control": Modifier.CTRL,
    "alt": Modifier.ALT,
    "opt": Modifier.ALT,
    "option": Modifier.ALT,
    "shift": Modifier.SHIFT,
    "super": Modifier.SUPER,
    "cmd": Modifier.SUPER,
    "command": Modifier.SUPER,
    "meta": Modifier.SUPER,
    "win": Modifier.SUPER,
}

SUPER_DISPLAY_NAMES: Final[Dict[System, str]] = {
    System.LINUX: "Super",
    System.WINDOWS: "Win",
    System.MACOS: "Cmd",
}

MODIFIER_KEYS: Final[Dict[Modifier, Tuple[int, int]]] = {
    Modifier.SUPER: (KEY_LEFT_SUPER, KEY_RIGHT_SUPER),
    Modifier.CTRL: (dpg.mvKey_LControl, dpg.mvKey_RControl),
    Modifier.ALT: (dpg.mvKey_LAlt, dpg.mvKey_RAlt),
    Modifier.SHIFT: (dpg.mvKey_LShift, dpg.mvKey_RShift),
}

RESERVED_MODIFIER_KEYS: Final[Dict[Modifier, int]] = {
    Modifier.SUPER: KEY_MODIFIER_SUPER,
    Modifier.CTRL: KEY_MODIFIER_CTRL,
    Modifier.ALT: KEY_MODIFIER_ALT,
    Modifier.SHIFT: KEY_MODIFIER_SHIFT,
}

MODIFIER_KEY_CODES: Final[FrozenSet[int]] = frozenset(
    key for keys in MODIFIER_KEYS.values() for key in keys
) | frozenset(RESERVED_MODIFIER_KEYS.values())


def is_modifier_key(key: int) -> bool:
    """Whether a press carries a modifier rather than the key a combination is built around.

    A modifier reaches a handler twice: under the key that carries it, and under the code ImGui
    reserves for the modifier itself. Both answer here, so an editor waiting for a combination keeps
    listening while either arrives.

    Args:
        key: The key code a press carries.

    Returns:
        bool: True while the press is a modifier being held.
    """
    return key in MODIFIER_KEY_CODES


def capture_modifiers() -> ModifierSet:
    """The modifiers held at the moment of the call, as DearPyGui reports their keys.

    Each modifier answers for both of its keys, so the left and right Ctrl are one ``CTRL``.
    """
    return frozenset(modifier for modifier, keys in MODIFIER_KEYS.items() if any(dpg.is_key_down(key) for key in keys))


def modifier_display(modifier: Modifier) -> str:
    """The name a modifier reads under on the platform in use.

    One key wears three names across the platforms — Command on macOS, Windows on Windows, Super on
    Linux — so a combination reads the way the keyboard in front of the reader is labelled. Every
    spelling stays readable everywhere through :data:`MODIFIER_NAMES`, which lets a scheme written
    for one platform be read on another.
    """
    if modifier is Modifier.SUPER:
        return SUPER_DISPLAY_NAMES[System.current()]

    return modifier.value


def modifiers_display(modifiers: ModifierSet) -> Tuple[str, ...]:
    """The display names of ``modifiers`` in the conventional Super, Ctrl, Alt, Shift order.

    Ordering by the declaration of :class:`Modifier` gives one combination one spelling wherever it
    is shown, whatever order the caller named its modifiers in.
    """
    return tuple(modifier_display(modifier) for modifier in Modifier if modifier in modifiers)
