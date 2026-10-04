from __future__ import annotations

from dataclasses import dataclass

from sampletones_application.utils.gui.keyboard.modifiers import (
    TYPING_MODIFIERS,
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

    @property
    def is_plain(self) -> bool:
        """Whether the press types its key, held alone or with Shift as a character is typed.

        Ctrl, Alt and Super make a press a command, which the shortcuts answer. A panel that reads
        keys as entry, such as a note or a hex digit, takes plain presses and yields the rest.
        """
        return self.modifiers <= TYPING_MODIFIERS

    @classmethod
    def capture(cls, key: int) -> KeyEvent:
        """Builds an event for ``key`` with the modifiers currently held."""
        return cls(key=key, modifiers=capture_modifiers())
