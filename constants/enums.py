from enum import StrEnum


class LibraryGeneratorName(StrEnum):
    PULSE = "pulse"
    TRIANGLE = "triangle"
    NOISE = "noise"


class GeneratorName(StrEnum):
    PULSE1 = "pulse1"
    PULSE2 = "pulse2"
    TRIANGLE = "triangle"
    NOISE = "noise"


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
