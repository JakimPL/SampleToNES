from dataclasses import dataclass
from math import ceil
from typing import Final

from sampletones_core.timing.rate import RowRate
from sampletones_shared.constants.nes import MAX_NES_FREQUENCY
from sampletones_shared.constants.project import MAX_SPEED, MIN_TEMPO

MIN_TICKS_PER_ROW: Final[int] = 1
MAX_TICKS_PER_ROW: Final[int] = ceil(
    RowRate.from_parameters(
        tempo=MIN_TEMPO,
        speed=MAX_SPEED,
        nes_frequency=MAX_NES_FREQUENCY,
    ).ticks_per_row
)


@dataclass(frozen=True)
class TickBounds:
    """The shortest and the longest an engine holds a row for, in ticks.

    In-app playback and the NSF reach every row the settings ask for, while a tracker's speed column
    states a narrower range, so each player names the range its rows are held within.

    Attributes:
        minimum: The fewest ticks a row lasts.
        maximum: The most ticks a row lasts.
    """

    minimum: int
    maximum: int


SONG_TICK_BOUNDS: Final[TickBounds] = TickBounds(
    minimum=MIN_TICKS_PER_ROW,
    maximum=MAX_TICKS_PER_ROW,
)
