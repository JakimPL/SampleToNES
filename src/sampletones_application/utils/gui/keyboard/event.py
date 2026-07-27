from __future__ import annotations

from dataclasses import dataclass

from sampletones_application.utils.gui.keyboard.modifiers import (
    ModifierSet,
    capture_modifiers,
)


@dataclass(frozen=True)
class KeyEvent:
    """A key press together with the modifiers held at the moment it fired.

    The router snapshots the modifiers once per event, so every scope reads the same set.
    """

    key: int
    modifiers: ModifierSet

    @classmethod
    def capture(cls, key: int) -> KeyEvent:
        """Builds an event for ``key`` with the modifiers currently held."""
        return cls(key=key, modifiers=capture_modifiers())
