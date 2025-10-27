from enum import Enum
from typing import List


class LibraryGeneratorName(Enum):
    PULSE = "pulse"
    TRIANGLE = "triangle"
    NOISE = "noise"


class GeneratorName(Enum):
    PULSE1 = "pulse1"
    PULSE2 = "pulse2"
    TRIANGLE = "triangle"
    NOISE = "noise"


class GeneratorClassName(Enum):
    PULSE_GENERATOR = "PulseGenerator"
    TRIANGLE_GENERATOR = "TriangleGenerator"
    NOISE_GENERATOR = "NoiseGenerator"


class InstructionClassName(Enum):
    PULSE_INSTRUCTION = "PulseInstruction"
    TRIANGLE_INSTRUCTION = "TriangleInstruction"
    NOISE_INSTRUCTION = "NoiseInstruction"


class FeatureKey(Enum):
    INITIAL_PITCH = "initial_pitch"
    VOLUME = "volume"
    ARPEGGIO = "arpeggio"
    PITCH = "pitch"
    HI_PITCH = "hi_pitch"
    DUTY_CYCLE = "duty_cycle"
