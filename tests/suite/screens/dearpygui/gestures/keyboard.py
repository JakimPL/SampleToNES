from typing import Sequence

from tests.suite.screens.dearpygui.gestures.arrival import Arrival
from tests.suite.screens.dearpygui.gestures.constants import HOLD_FRAMES, RELEASE_FRAMES, SETTLE_FRAMES
from tests.suite.screens.dearpygui.keys import IMGUI_LEFT_SHIFT, keysym_of, keysym_of_character


class Keyboard(Arrival):
    """The keyboard of a hand: key presses with modifiers, and typed text.

    It owns every gesture made with keys and builds each from `Arrival`'s steps: key down, confirm the
    key reads as held, key up and settle. The full hand also uses it to replace the text of a field.
    """

    def press_key(
        self,
        key: int,
        *,
        modifiers: Sequence[int],
    ) -> None:
        """Presses the Dear ImGui key ``key`` while holding the Dear ImGui keys in ``modifiers``."""
        for modifier in modifiers:
            self._device.key_down(keysym_of(modifier))
        if modifiers:
            self._settle(HOLD_FRAMES)
            self._confirm_keys(modifiers)

        self._device.key_down(keysym_of(key))
        self._settle(HOLD_FRAMES)
        self._confirm_keys([key])
        self._device.key_up(keysym_of(key))
        self._settle(RELEASE_FRAMES)
        for modifier in reversed(modifiers):
            self._device.key_up(keysym_of(modifier))

        self._settle(SETTLE_FRAMES)

    def type_text(self, text: str) -> None:
        """Types ``text`` into whatever holds the keyboard, one character a frame."""
        shift = keysym_of(IMGUI_LEFT_SHIFT)
        for character in text:
            keysym = keysym_of_character(character)
            shifted = self._device.needs_shift(keysym)
            if shifted:
                self._device.key_down(shift)

            self._tap(keysym)
            if shifted:
                self._device.key_up(shift)

        self._settle(SETTLE_FRAMES)

    def _tap(self, keysym: int) -> None:
        self._device.key_down(keysym)
        self._settle(HOLD_FRAMES)
        self._device.key_up(keysym)
        self._settle(RELEASE_FRAMES)
