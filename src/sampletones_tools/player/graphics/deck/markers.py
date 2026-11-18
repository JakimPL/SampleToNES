from dataclasses import dataclass
from typing import Final

from sampletones_tools.player.graphics.deck.groups import FIRST_PIN_GROUP, SECOND_PIN_GROUP

PIXELS_PER_PITCH: Final[int] = 2
PIN_STEM_COLUMN: Final[int] = 3
FIRST_SPRITE_PALETTE: Final[int] = 0
SECOND_SPRITE_PALETTE: Final[int] = 1
MARKER_SLOTS: Final[int] = 3


@dataclass(frozen=True)
class Pin:
    """The marker a channel moves along the keyboard: its tile and the palette it takes."""

    group: str
    member: str
    palette: int


PULSE1_PIN: Final[Pin] = Pin(FIRST_PIN_GROUP, "pin_high", FIRST_SPRITE_PALETTE)
PULSE2_PIN: Final[Pin] = Pin(SECOND_PIN_GROUP, "pin_middle", FIRST_SPRITE_PALETTE)
TRIANGLE_PIN: Final[Pin] = Pin(FIRST_PIN_GROUP, "pin_low", SECOND_SPRITE_PALETTE)
