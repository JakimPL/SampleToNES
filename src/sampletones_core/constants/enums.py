from __future__ import annotations

import re
from enum import StrEnum
from typing import Dict, Final, List, Literal


class LibraryGeneratorName(StrEnum):
    PULSE = "pulse"
    TRIANGLE = "triangle"
    NOISE = "noise"


class GeneratorName(StrEnum):
    PULSE1 = "pulse1"
    PULSE2 = "pulse2"
    TRIANGLE = "triangle"
    NOISE = "noise"

    @property
    def capitalized(self) -> str:
        spaced_value = re.sub(r"(\d+)", r" \1", self.value)
        return spaced_value.capitalize()

    @classmethod
    def items(cls) -> List[GeneratorName]:
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


GENERATOR_ABBREVIATIONS: Final[Dict[GeneratorName, Literal["P", "p", "T", "N"]]] = {
    GeneratorName.PULSE1: "P",
    GeneratorName.PULSE2: "p",
    GeneratorName.TRIANGLE: "T",
    GeneratorName.NOISE: "N",
}


GENERATOR_ABBREVIATION_TO_NAME: Final[Dict[str, GeneratorName]] = {
    abbreviation: name for name, abbreviation in GENERATOR_ABBREVIATIONS.items()
}


GENERATOR_ABBREVIATION_PATTERN: Final[str] = rf"^[{''.join(GENERATOR_ABBREVIATIONS.values())}]+$"


DEFAULT_GENERATORS: Final[List[GeneratorName]] = [
    GeneratorName.PULSE1,
    GeneratorName.TRIANGLE,
    GeneratorName.NOISE,
]


def abbreviate_generator_names(generator_names: List[GeneratorName]) -> str:
    return "".join(GENERATOR_ABBREVIATIONS[name] for name in generator_names)
