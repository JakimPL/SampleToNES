from typing import Dict

from configs.config import Config
from timers.phase import PhaseTimer
from utils.frequencies import pitch_to_frequency


def get_frequency_table(config: Config) -> Dict[int, float]:
    timer = PhaseTimer(sample_rate=config.library.sample_rate, change_rate=config.library.change_rate)
    frequencies = {}
    for note in range(config.general.min_pitch, config.general.max_pitch + 1):
        frequency = pitch_to_frequency(note, config.library.a4_frequency, config.library.a4_pitch)
        timer.frequency = frequency
        frequencies[note] = timer.frequency

    return frequencies
