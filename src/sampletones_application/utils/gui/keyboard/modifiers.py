from enum import Enum
from typing import Dict, Final, FrozenSet, Tuple

import dearpygui.dearpygui as dpg


class Modifier(Enum):
    """A modifier key a press carries, declared in the order a combination displays them."""

    CTRL = "Ctrl"
    ALT = "Alt"
    SHIFT = "Shift"


ModifierSet = FrozenSet[Modifier]

NO_MODIFIERS: Final[ModifierSet] = frozenset()
CTRL: Final[ModifierSet] = frozenset({Modifier.CTRL})
ALT: Final[ModifierSet] = frozenset({Modifier.ALT})
SHIFT: Final[ModifierSet] = frozenset({Modifier.SHIFT})
CTRL_ALT: Final[ModifierSet] = frozenset({Modifier.CTRL, Modifier.ALT})
CTRL_SHIFT: Final[ModifierSet] = frozenset({Modifier.CTRL, Modifier.SHIFT})
CTRL_ALT_SHIFT: Final[ModifierSet] = frozenset({Modifier.CTRL, Modifier.ALT, Modifier.SHIFT})

MODIFIER_KEYS: Final[Dict[Modifier, Tuple[int, int]]] = {
    Modifier.CTRL: (dpg.mvKey_LControl, dpg.mvKey_RControl),
    Modifier.ALT: (dpg.mvKey_LAlt, dpg.mvKey_RAlt),
    Modifier.SHIFT: (dpg.mvKey_LShift, dpg.mvKey_RShift),
}


def capture_modifiers() -> ModifierSet:
    """The modifiers held at the moment of the call, as DearPyGui reports their keys.

    Each modifier answers for both of its keys, so the left and right Ctrl are one ``CTRL``.
    """
    return frozenset(modifier for modifier, keys in MODIFIER_KEYS.items() if any(dpg.is_key_down(key) for key in keys))


def modifiers_display(modifiers: ModifierSet) -> Tuple[str, ...]:
    """The display names of ``modifiers`` in the conventional Ctrl, Alt, Shift order.

    Ordering by the declaration of :class:`Modifier` gives one combination one spelling wherever it
    is shown, whatever order the caller named its modifiers in.
    """
    return tuple(modifier.value for modifier in Modifier if modifier in modifiers)
