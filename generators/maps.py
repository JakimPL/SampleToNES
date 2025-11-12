from typing import Dict

from constants import GeneratorClassName, GeneratorName, LibraryGeneratorName
from constants.general import MIXER_NOISE, MIXER_PULSE, MIXER_TRIANGLE
from instructions import (
    InstructionClass,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)

from .noise import NoiseGenerator
from .pulse import PulseGenerator
from .triangle import TriangleGenerator
from .typehints import GeneratorClass

LIBRARY_GENERATOR_CLASS_MAP: Dict[LibraryGeneratorName, GeneratorClassName] = {
    LibraryGeneratorName.PULSE: GeneratorClassName.PULSE_GENERATOR,
    LibraryGeneratorName.TRIANGLE: GeneratorClassName.TRIANGLE_GENERATOR,
    LibraryGeneratorName.NOISE: GeneratorClassName.NOISE_GENERATOR,
}

GENERATOR_CLASSES: Dict[GeneratorName, GeneratorClass] = {
    GeneratorName.PULSE1: PulseGenerator,
    GeneratorName.PULSE2: PulseGenerator,
    GeneratorName.TRIANGLE: TriangleGenerator,
    GeneratorName.NOISE: NoiseGenerator,
}


GENERATOR_CLASS_MAP: Dict[GeneratorClassName, GeneratorClass] = {
    GeneratorClassName.PULSE_GENERATOR: PulseGenerator,
    GeneratorClassName.TRIANGLE_GENERATOR: TriangleGenerator,
    GeneratorClassName.NOISE_GENERATOR: NoiseGenerator,
}


INSTRUCTION_TO_GENERATOR_MAP: Dict[InstructionClass, GeneratorClass] = {
    TriangleInstruction: TriangleGenerator,
    PulseInstruction: PulseGenerator,
    NoiseInstruction: NoiseGenerator,
}


MIXER_LEVELS: Dict[GeneratorClassName, float] = {
    GeneratorClassName.PULSE_GENERATOR: MIXER_PULSE,
    GeneratorClassName.NOISE_GENERATOR: MIXER_NOISE,
    GeneratorClassName.TRIANGLE_GENERATOR: MIXER_TRIANGLE,
}
