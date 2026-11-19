from enum import IntFlag
from typing import Final

from sampletones_player.specification.binary import MAX_BYTE_VALUE
from sampletones_tools.console.rom.registers import CONTROLLER_DATA_MASK, OPEN_BUS

READ_OUT_BIT: Final[int] = 0x80


class Button(IntFlag):
    """The buttons of a standard controller, each at the place its read falls in the serial order."""

    A = 0x01
    B = 0x02
    SELECT = 0x04
    START = 0x08
    UP = 0x10
    DOWN = 0x20
    LEFT = 0x40
    RIGHT = 0x80


NO_BUTTONS: Final[Button] = Button(0)


class Controller:
    """A standard controller as a program reads it: a strobe that latches the buttons, then one bit a read.

    While the strobe stands high the controller keeps reloading, so every read answers with the
    first button. Dropping the strobe latches the eight buttons, and each read after that answers
    with the next one in the order A, B, Select, Start, Up, Down, Left, Right. A read past the
    eighth answers with a set bit, as the official controller does. The button arrives in bit 0,
    under the bit the open bus leaves set.
    """

    def __init__(self) -> None:
        self._held = NO_BUTTONS
        self._strobed = False
        self._latched = MAX_BYTE_VALUE

    def hold(self, buttons: Button) -> None:
        """Holds ``buttons`` down, and releases every other one."""
        self._held = buttons

    def write(self, value: int) -> None:
        """Takes a store to the strobe register, latching the buttons while its low bit stands or falls."""
        strobed = bool(value & CONTROLLER_DATA_MASK)
        if strobed or self._strobed:
            self._latched = int(self._held)

        self._strobed = strobed

    def read(self) -> int:
        """Answers one serial read: the next button, or the first one while the strobe stands high."""
        if self._strobed:
            return OPEN_BUS | (int(self._held) & CONTROLLER_DATA_MASK)

        pressed = self._latched & CONTROLLER_DATA_MASK
        self._latched = (self._latched >> 1) | READ_OUT_BIT
        return OPEN_BUS | pressed
