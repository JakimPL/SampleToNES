from typing import Dict

from sampletones_core.configs import Config
from sampletones_shared.constants.music import LIMIT_MAX_PITCH, LIMIT_MIN_PITCH
from sampletones_shared.music import Tuning

from .arithmetic import frequency_to_timer
from .implementation.phase import PhaseTimer


def get_frequency_table(config: Config) -> Dict[int, float]:
    timer = PhaseTimer(
        sample_rate=config.library.sample_rate,
        nes_frequency=config.library.nes_frequency,
    )
    tuning = config.library.tuning
    frequencies = {}

    for note in range(config.general.min_pitch, config.general.max_pitch + 1):
        timer.frequency = tuning.frequency(note)
        frequencies[note] = timer.frequency

    return frequencies


def get_timer_table(tuning: Tuning) -> Dict[int, int]:
    """The timer register value each pitch sounds at.

    A pitch reaches the hardware as the divider producing the frequency nearest to it, and the
    tuning is the whole of what decides which frequency that is — the same relation the
    generators render from, stated in the terms the registers take. The table spans every pitch
    the project sounds, so a stream naming any of them resolves.

    Args:
        tuning: Where concert pitch sits for the reconstruction being written.

    Returns:
        Dict[int, int]: The timer value for every pitch from ``LIMIT_MIN_PITCH`` to
            ``LIMIT_MAX_PITCH``.
    """
    return {pitch: frequency_to_timer(tuning.frequency(pitch)) for pitch in range(LIMIT_MIN_PITCH, LIMIT_MAX_PITCH + 1)}
