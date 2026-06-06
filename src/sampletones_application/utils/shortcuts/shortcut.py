from dataclasses import dataclass
from typing import Optional, Tuple

from sampletones_application.utils.shortcuts.keys import (
    KEY_DISPLAY_NAMES,
    Modifier,
)


@dataclass(frozen=True)
class Shortcut:
    key: Optional[int] = None
    modifiers: Tuple[Modifier, ...] = ()

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
