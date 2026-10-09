from enum import StrEnum


class NSFRepeat(StrEnum):
    """Where a program goes once its song reaches the end."""

    ONCE = "once"
    FROM_START = "from_start"
    FROM_FRAME = "from_frame"
