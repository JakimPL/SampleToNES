from __future__ import annotations

import re
from enum import StrEnum
from typing import Dict, Final, List, Literal


class GeneratorName(StrEnum):
    PULSE = "pulse"
    TRIANGLE = "triangle"
    NOISE = "noise"


class ChannelName(StrEnum):
    PULSE1 = "pulse1"
    PULSE2 = "pulse2"
    TRIANGLE = "triangle"
    NOISE = "noise"

    @property
    def capitalized(self) -> str:
        spaced_value = re.sub(r"(\d+)", r" \1", self.value)
        return spaced_value.capitalize()

    @classmethod
    def items(cls) -> List[ChannelName]:
        return [cls.PULSE1, cls.PULSE2, cls.TRIANGLE, cls.NOISE]


class GeneratorClassName(StrEnum):
    PULSE_GENERATOR = "PulseGenerator"
    TRIANGLE_GENERATOR = "TriangleGenerator"
    NOISE_GENERATOR = "NoiseGenerator"


class InstructionClassName(StrEnum):
    PULSE_INSTRUCTION = "PulseInstruction"
    TRIANGLE_INSTRUCTION = "TriangleInstruction"
    NOISE_INSTRUCTION = "NoiseInstruction"


class FeatureKey(StrEnum):
    INITIAL_PITCH = "initial_pitch"
    VOLUME = "volume"
    ARPEGGIO = "arpeggio"
    PITCH = "pitch"
    HI_PITCH = "hi_pitch"
    DUTY_CYCLE = "duty_cycle"

    @property
    def capitalized(self) -> str:
        return self.value.replace("_", " ").capitalize()


class AudioSourceType(StrEnum):
    RECONSTRUCTION = "reconstruction"
    ORIGINAL = "original"


class SpectralDistance(StrEnum):
    SQUARED = "squared"
    ABSOLUTE = "absolute"
    BETA_DIVERGENCE = "beta_divergence"


class PhaseAlignerName(StrEnum):
    SLIDING_RMSE = "sliding_rmse"
    CROSS_CORRELATION = "cross_correlation"


class SelectorName(StrEnum):
    GREEDY = "greedy"
    VITERBI = "viterbi"


class SpectrumMethod(StrEnum):
    FFT = "fft"
    LOG_SPACED_FFT = "logfft"
    CQT = "cqt"


class CQTWindow(StrEnum):
    HANN = "hann"
    RECTANGULAR = "rectangular"


CHANNEL_ABBREVIATIONS: Final[Dict[ChannelName, Literal["P", "p", "T", "N"]]] = {
    ChannelName.PULSE1: "P",
    ChannelName.PULSE2: "p",
    ChannelName.TRIANGLE: "T",
    ChannelName.NOISE: "N",
}


CHANNEL_ABBREVIATION_TO_NAME: Final[Dict[str, ChannelName]] = {
    abbreviation: name for name, abbreviation in CHANNEL_ABBREVIATIONS.items()
}


CHANNEL_ABBREVIATION_PATTERN: Final[str] = rf"^[{''.join(CHANNEL_ABBREVIATIONS.values())}]+$"


DEFAULT_CHANNELS: Final[List[ChannelName]] = [
    ChannelName.PULSE1,
    ChannelName.TRIANGLE,
    ChannelName.NOISE,
]


def abbreviate_channel_names(channel_names: List[ChannelName]) -> str:
    return "".join(CHANNEL_ABBREVIATIONS[name] for name in channel_names)
