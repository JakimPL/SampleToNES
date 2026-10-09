from functools import partial
from typing import Sequence

from automation.dearpygui.bridge import ONE_FRAME
from automation.dearpygui.gestures.arrival import Arrival
from automation.dearpygui.gestures.constants import HOLD_FRAMES, SETTLE_FRAMES
from automation.dearpygui.keys import (
    IMGUI_LEFT_SHIFT,
    key_name,
    keysym_of,
    keysym_of_character,
)


class Keyboard(Arrival):
    """The keyboard of a hand: key presses with modifiers, and typed text.

    It owns every gesture made with keys and builds each from `Arrival`'s steps. Modifiers go down first and
    read as held, and the key itself goes down and comes up in one go, so Dear ImGui reads it down for a
    single frame at any frame rate, the one press a person made, and the witness confirms its release. The
    full hand also uses it to replace the text of a field.
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
        try:
            if modifiers:
                self._settle(HOLD_FRAMES)
                self._confirm_keys(modifiers)

            released = partial(self._witness.key_releases, key)
            before = self._bridge.ask(released)
            self._device.tap_key(keysym_of(key))
            self._await_count(released, before + 1, f"The key {key_name(key)}")
        finally:
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
            try:
                self._device.tap_key(keysym)
                self._settle(ONE_FRAME)
            finally:
                if shifted:
                    self._device.key_up(shift)

        self._settle(SETTLE_FRAMES)
