from typing import Dict

from sampletones_core.configs import Config
from sampletones_core.utils.frequencies import pitch_to_frequency

from .implementation.phase import PhaseTimer


def get_frequency_table(config: Config) -> Dict[int, float]:
    timer = PhaseTimer(
        sample_rate=config.library.sample_rate,
        nes_frequency=config.library.nes_frequency,
    )
    frequencies = {}

    for note in range(config.general.min_pitch, config.general.max_pitch + 1):
        frequency = pitch_to_frequency(
            note,
            config.library.a4_frequency,
            config.library.a4_pitch,
        )
        timer.frequency = frequency
        frequencies[note] = timer.frequency

    return frequencies
