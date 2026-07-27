from dataclasses import dataclass
from typing import Optional

from sampletones_application.utils.gui.keyboard.modifiers import (
    NO_MODIFIERS,
    ModifierSet,
    modifiers_display,
)
from sampletones_application.utils.gui.shortcuts.keys import KEY_DISPLAY_NAMES


@dataclass(frozen=True)
class Shortcut:
    """A key plus its required modifiers, and whether it fires while a field is focused.

    ``field_transparent`` shortcuts (e.g. switching tabs) outrank text entry and fire even
    while an input owns the keyboard; the rest stay behind field focus so their keys reach
    the field.
    """

    key: Optional[int] = None
    modifiers: ModifierSet = NO_MODIFIERS
    field_transparent: bool = False

    def get_display_string(self) -> str:
        if self.key is None:
            return ""

        return "+".join((*modifiers_display(self.modifiers), self._key_to_string()))

    def _key_to_string(self) -> str:
        if self.key is None:
            return ""

        return KEY_DISPLAY_NAMES.get(self.key, "?")
