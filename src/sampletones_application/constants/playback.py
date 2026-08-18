from enum import StrEnum
from math import ceil
from typing import Final

from sampletones_core.timing import RowRate
from sampletones_shared.constants.nes import MAX_NES_FREQUENCY
from sampletones_shared.constants.project import MAX_SPEED, MIN_TEMPO


class FollowMode(StrEnum):
    """How far the sequencer view chases the playhead during song playback.

    The two predicates are the whole contract: following rows is following patterns with the grid
    scrolled to the sounding row as well, stated once here so every surface reads the same rule.
    """

    ROWS = "rows"
    PATTERNS = "patterns"
    OFF = "off"

    @property
    def follows_pattern(self) -> bool:
        """Whether the tracker shows the order frame the playhead sounds."""
        return self in (FollowMode.ROWS, FollowMode.PATTERNS)

    @property
    def follows_row(self) -> bool:
        """Whether the tracker keeps the sounding row within the visible band."""
        return self is FollowMode.ROWS


DEFAULT_FOLLOW_MODE: Final[FollowMode] = FollowMode.ROWS

MIN_TICKS_PER_ROW: Final[int] = 1
MAX_TICKS_PER_ROW: Final[int] = ceil(
    RowRate.from_parameters(
        tempo=MIN_TEMPO,
        speed=MAX_SPEED,
        nes_frequency=MAX_NES_FREQUENCY,
    ).ticks_per_row
)
