from typing import Dict, Final

from sampletones_core.constants.enums import (
    ChannelName,
    GeneratorClassName,
    LibraryGeneratorName,
)
from sampletones_core.constants.general import (
    MIXER_NOISE,
    MIXER_PULSE,
    MIXER_TRIANGLE,
)
from sampletones_core.instructions import (
    InstructionTypeUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)

from .implementation.noise import NoiseGenerator
from .implementation.pulse import PulseGenerator
from .implementation.triangle import TriangleGenerator
from .types import GeneratorTypeUnion

LIBRARY_GENERATOR_CLASS_MAP: Final[Dict[LibraryGeneratorName, GeneratorClassName]] = {
    LibraryGeneratorName.PULSE: GeneratorClassName.PULSE_GENERATOR,
    LibraryGeneratorName.TRIANGLE: GeneratorClassName.TRIANGLE_GENERATOR,
    LibraryGeneratorName.NOISE: GeneratorClassName.NOISE_GENERATOR,
}


CHANNEL_CLASSES: Final[Dict[ChannelName, GeneratorTypeUnion]] = {
    ChannelName.PULSE1: PulseGenerator,
    ChannelName.PULSE2: PulseGenerator,
    ChannelName.TRIANGLE: TriangleGenerator,
    ChannelName.NOISE: NoiseGenerator,
}


GENERATOR_CLASS_MAP: Final[Dict[GeneratorClassName, GeneratorTypeUnion]] = {
    GeneratorClassName.PULSE_GENERATOR: PulseGenerator,
    GeneratorClassName.TRIANGLE_GENERATOR: TriangleGenerator,
    GeneratorClassName.NOISE_GENERATOR: NoiseGenerator,
}


INSTRUCTION_TO_GENERATOR_MAP: Final[Dict[InstructionTypeUnion, GeneratorTypeUnion]] = {
    PulseInstruction: PulseGenerator,
    TriangleInstruction: TriangleGenerator,
    NoiseInstruction: NoiseGenerator,
}

GENERATOR_TO_INSTRUCTION_MAP: Final[Dict[GeneratorTypeUnion, InstructionTypeUnion]] = {
    PulseGenerator: PulseInstruction,
    TriangleGenerator: TriangleInstruction,
    NoiseGenerator: NoiseInstruction,
}


MIXER_LEVELS: Final[Dict[GeneratorClassName, float]] = {
    GeneratorClassName.PULSE_GENERATOR: MIXER_PULSE,
    GeneratorClassName.TRIANGLE_GENERATOR: MIXER_TRIANGLE,
    GeneratorClassName.NOISE_GENERATOR: MIXER_NOISE,
}
