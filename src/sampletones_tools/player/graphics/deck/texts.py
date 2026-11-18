from typing import Final

from sampletones_core.constants.general import MAX_PERIOD
from sampletones_core.utils.frequencies import period_to_name, pitch_to_name
from sampletones_shared.constants.music import LIMIT_MIN_PITCH

UNKNOWN_CHARACTER: Final[str] = "?"
REST_NOTE: Final[str] = "---"
SECONDS_PER_MINUTE: Final[int] = 60


def pitch_name(pitch: int) -> str:
    """The name a tone channel's pitch index is shown under, the way the application names pitches."""
    return pitch_to_name(LIMIT_MIN_PITCH + pitch)


def noise_name(period: int) -> str:
    """The name a noise register's period is shown under, the way the application names periods."""
    return period_to_name(MAX_PERIOD - period)


def clock_text(seconds: int) -> str:
    """A length of time as minutes and seconds, two digits each."""
    return f"{seconds // SECONDS_PER_MINUTE:02d}:{seconds % SECONDS_PER_MINUTE:02d}"
