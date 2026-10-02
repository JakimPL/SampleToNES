from enum import IntEnum
from typing import Final

from Xlib import X
from Xlib.display import Display
from Xlib.ext import xtest

from tests.suite.screens.dearpygui.geometry import Point

SHIFTED_COLUMN: Final[int] = 1


class MouseButton(IntEnum):
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3
    WHEEL_UP = 4
    WHEEL_DOWN = 5


class UntypableCharacterError(LookupError):
    """Raised when the display's keyboard map holds no key that types a character."""


class XTestDevice:
    """The pointer and the keyboard of one X display, driven through the XTEST extension.

    Each call sends one event and flushes it, so the server holds it before the next frame polls.
    The display is the scenario's own, which keeps every event inside the application under test.
    The display repeats no held key, so a key held across a slow frame arrives as the one press a
    person made.
    """

    def __init__(self, display_name: str) -> None:
        self._display = Display(display_name)
        self._display.change_keyboard_control(auto_repeat_mode=X.AutoRepeatModeOff)
        self._display.sync()

    def move(self, point: Point) -> None:
        xtest.fake_input(self._display, X.MotionNotify, x=point.x, y=point.y)
        self._display.sync()

    def button_down(self, button: MouseButton) -> None:
        xtest.fake_input(self._display, X.ButtonPress, int(button))
        self._display.sync()

    def button_up(self, button: MouseButton) -> None:
        xtest.fake_input(self._display, X.ButtonRelease, int(button))
        self._display.sync()

    def key_down(self, keysym: int) -> None:
        xtest.fake_input(self._display, X.KeyPress, self._keycode(keysym))
        self._display.sync()

    def key_up(self, keysym: int) -> None:
        xtest.fake_input(self._display, X.KeyRelease, self._keycode(keysym))
        self._display.sync()

    def needs_shift(self, keysym: int) -> bool:
        """Whether typing ``keysym`` takes Shift, which is where the keyboard map shifts it."""
        keycode = self._keycode(keysym)
        return self._display.keycode_to_keysym(keycode, 0) != keysym and (
            self._display.keycode_to_keysym(keycode, SHIFTED_COLUMN) == keysym
        )

    def close(self) -> None:
        self._display.close()

    def _keycode(self, keysym: int) -> int:
        keycode = self._display.keysym_to_keycode(keysym)
        if keycode == 0:
            raise UntypableCharacterError(f"The keyboard map holds no key for the keysym {keysym:#x}")

        return int(keycode)
