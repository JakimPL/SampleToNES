from enum import IntEnum
from typing import Final

from Xlib import X
from Xlib.display import Display
from Xlib.ext import xtest

from tests.suite.screens.dearpygui.geometry import Point

SHIFTED_COLUMN: Final[int] = 1
BITS_PER_BYTE: Final[int] = 8


class MouseButton(IntEnum):
    """A pointer button as the X server numbers it, the two wheel directions included."""

    LEFT = 1
    MIDDLE = 2
    RIGHT = 3
    WHEEL_UP = 4
    WHEEL_DOWN = 5

    @property
    def mask(self) -> int:
        """The bit the pointer's state carries while this button is down."""
        return X.Button1Mask << (self.value - 1)


class UntypableCharacterError(LookupError):
    """Raised when the display's keyboard map holds no key that types a character."""


class XTestDevice:
    """The pointer and the keyboard of one X display, driven through the XTEST extension.

    Each call sends its events and flushes them, so the server holds them before the next frame polls.
    The display belongs to the worker, which keeps every event inside the application under test, and
    the worker's scenarios take it in turn. The device therefore starts and ends with every key and
    button up, so a scenario that failed halfway through a gesture leaves nothing held for the next.
    The display turns key auto-repeat off, so a key held across a slow frame arrives as the one
    press a person made.
    """

    def __init__(self, display_name: str) -> None:
        self._display = Display(display_name)
        self._display.change_keyboard_control(auto_repeat_mode=X.AutoRepeatModeOff)
        self.release_everything()

    def move(self, point: Point) -> None:
        """Moves the pointer to ``point``, in display pixels."""
        xtest.fake_input(self._display, X.MotionNotify, x=point.x, y=point.y)
        self._display.sync()

    def button_down(self, button: MouseButton) -> None:
        """Presses ``button`` and holds it down."""
        xtest.fake_input(self._display, X.ButtonPress, int(button))
        self._display.sync()

    def button_up(self, button: MouseButton) -> None:
        """Releases ``button``."""
        xtest.fake_input(self._display, X.ButtonRelease, int(button))
        self._display.sync()

    def click_button(
        self,
        button: MouseButton,
        presses: int,
    ) -> None:
        """Presses and releases ``button`` ``presses`` times in one go.

        Dear ImGui reads each press and each release on a frame of its own, so a press stands down for a
        single frame and the presses land two frames apart, the closest a display brings them.
        """
        for _ in range(presses):
            xtest.fake_input(self._display, X.ButtonPress, int(button))
            xtest.fake_input(self._display, X.ButtonRelease, int(button))
        self._display.sync()

    def tap_key(self, keysym: int) -> None:
        """Presses and releases the key typing ``keysym`` in one go.

        Dear ImGui reads the press on one frame and the release on the next, so the key stands down for a
        single frame at any frame rate, too briefly to repeat.
        """
        keycode = self._keycode(keysym)
        xtest.fake_input(self._display, X.KeyPress, keycode)
        xtest.fake_input(self._display, X.KeyRelease, keycode)
        self._display.sync()

    def key_down(self, keysym: int) -> None:
        """Presses the key typing ``keysym`` and holds it down."""
        xtest.fake_input(self._display, X.KeyPress, self._keycode(keysym))
        self._display.sync()

    def key_up(self, keysym: int) -> None:
        """Releases the key typing ``keysym``."""
        xtest.fake_input(self._display, X.KeyRelease, self._keycode(keysym))
        self._display.sync()

    def needs_shift(self, keysym: int) -> bool:
        """Whether typing ``keysym`` takes Shift, which is where the keyboard map shifts it."""
        keycode = self._keycode(keysym)
        return self._display.keycode_to_keysym(keycode, 0) != keysym and (
            self._display.keycode_to_keysym(keycode, SHIFTED_COLUMN) == keysym
        )

    def release_everything(self) -> None:
        """Lets go of every key and button the display holds down, whichever gesture pressed it."""
        for index, byte in enumerate(self._display.query_keymap()):
            for bit in range(BITS_PER_BYTE):
                if byte & (1 << bit):
                    xtest.fake_input(self._display, X.KeyRelease, index * BITS_PER_BYTE + bit)

        mask = self._display.screen().root.query_pointer().mask
        for button in MouseButton:
            if mask & button.mask:
                xtest.fake_input(self._display, X.ButtonRelease, int(button))
        self._display.sync()

    def close(self) -> None:
        """Lets go of everything still held and closes the connection to the display."""
        self.release_everything()
        self._display.close()

    def _keycode(self, keysym: int) -> int:
        keycode = self._display.keysym_to_keycode(keysym)
        if keycode == 0:
            raise UntypableCharacterError(f"The keyboard map holds no key for the keysym {keysym:#x}")

        return int(keycode)
