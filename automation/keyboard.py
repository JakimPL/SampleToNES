from typing import Final

from automation.dearpygui.hand import Hand
from sampletones_application.utils.gui.keyboard.combination import (
    KeyCombination,
)
from sampletones_application.utils.gui.keyboard.modifiers import (
    MODIFIER_KEYS,
    Modifier,
)
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut

LEFT_KEY: Final[int] = 0
PRIMARY_COMBINATION: Final[int] = 0
FIRST_ALIAS: Final[int] = 0


def primary_combination(shortcut: Shortcut) -> KeyCombination:
    """The combination an action displays, which is the one a person presses."""
    return shortcut.combinations()[PRIMARY_COMBINATION]


def first_alias(shortcut: Shortcut) -> KeyCombination:
    """The first further combination an action answers to, beside the one it displays."""
    return shortcut.aliases[FIRST_ALIAS]


def press_combination(hand: Hand, combination: KeyCombination) -> None:
    """Presses ``combination`` on the real keyboard: its modifiers on the left side, then its key.

    Modifiers go down in the order a combination displays them, which is the order a person holds them.
    """
    modifiers = [MODIFIER_KEYS[modifier][LEFT_KEY] for modifier in Modifier if modifier in combination.modifiers]
    hand.press_key(combination.key, modifiers=modifiers)
