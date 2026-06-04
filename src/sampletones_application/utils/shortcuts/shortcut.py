from dataclasses import dataclass
from typing import Tuple

from sampletones_application.utils.shortcuts.keys import (
    KEY_DISPLAY_NAMES,
    Modifier,
)


@dataclass(frozen=True)
class Shortcut:
    key: int
    modifiers: Tuple[Modifier, ...] = ()

    def get_display_string(self) -> str:
        parts = [modifier.value for modifier in self.modifiers]
        parts.append(self._key_to_string())
        return "+".join(parts)

    def _key_to_string(self) -> str:
        return KEY_DISPLAY_NAMES.get(self.key, "?")
