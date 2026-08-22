from enum import StrEnum
from typing import Final


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
