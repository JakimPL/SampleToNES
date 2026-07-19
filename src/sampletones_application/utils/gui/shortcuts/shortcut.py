from dataclasses import dataclass
from typing import Optional, Tuple

from sampletones_application.utils.gui.shortcuts.keys import (
    KEY_DISPLAY_NAMES,
    Modifier,
)


@dataclass(frozen=True)
class Shortcut:
    """A key plus its required modifiers, and whether it fires while a field is focused.

    ``field_transparent`` shortcuts (e.g. switching tabs) outrank text entry and fire even
    while an input owns the keyboard; the rest stay behind field focus so their keys reach
    the field.
    """

    key: Optional[int] = None
    modifiers: Tuple[Modifier, ...] = ()
    field_transparent: bool = False

    @property
    def is_bindable(self) -> bool:
        return self.key is not None

    def get_display_string(self) -> str:
        if self.key is None:
            return ""

        parts = [modifier.value for modifier in self.modifiers]
        parts.append(self._key_to_string())
        return "+".join(parts)

    def _key_to_string(self) -> str:
        if self.key is None:
            return ""

        return KEY_DISPLAY_NAMES.get(self.key, "?")
