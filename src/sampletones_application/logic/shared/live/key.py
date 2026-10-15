from dataclasses import dataclass
from enum import Enum


class Keyboard(Enum):
    """The keyboard a key is played on, which decides how its release treats a recording."""

    MIDI = "midi"
    COMPUTER = "computer"


@dataclass(frozen=True)
class LiveKey:
    """One key of one keyboard, the identity a press and its release share.

    A key on each keyboard is its own key, so a MIDI note and a computer key naming the same pitch are
    held, released and returned to apart.

    Attributes:
        keyboard: The keyboard the key is on.
        number: The key on that keyboard: a MIDI note number, or the computer key's code.
    """

    keyboard: Keyboard
    number: int
