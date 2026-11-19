from typing import Dict, Final, Iterable

from sampletones_core.configs import Config
from sampletones_shared.constants.music import LIMIT_MAX_PITCH, LIMIT_MIN_PITCH
from sampletones_shared.music import Tuning

from .arithmetic import frequency_to_timer, timer_to_frequency

SOUNDED_PITCHES: Final[range] = range(LIMIT_MIN_PITCH, LIMIT_MAX_PITCH + 1)


def get_frequency_table(config: Config) -> Dict[int, float]:
    """The frequency each note a library holds tonal instructions for sounds at: the frequency of
    the divider its tuned frequency lies nearest, read off the one timer table."""
    timers = get_timer_table(config.library.tuning, config.general.pitch_range.pitches)
    return {pitch: timer_to_frequency(timer) for pitch, timer in timers.items()}


def get_timer_table(tuning: Tuning, pitches: Iterable[int] = SOUNDED_PITCHES) -> Dict[int, int]:
    """The timer register value each pitch sounds at.

    A pitch reaches the hardware as the divider producing the frequency nearest to it, and the
    tuning is the whole of what decides which frequency that is — the same relation the
    generators render from, stated in the terms the registers take. By default the table spans
    every pitch the project sounds, so a stream naming any of them resolves.

    Args:
        tuning: Where concert pitch sits for the reconstruction being written.
        pitches: The pitches the table names.

    Returns:
        Dict[int, int]: The timer value for every pitch named.
    """
    return {pitch: frequency_to_timer(tuning.frequency(pitch)) for pitch in pitches}
