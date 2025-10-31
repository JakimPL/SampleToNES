from typing import Dict, cast

from constants.general import MIXER_NOISE, MIXER_PULSE, MIXER_TRIANGLE
from exporters.noise import NoiseExporter
from exporters.pulse import PulseExporter
from exporters.triangle import TriangleExporter
from generators.noise import NoiseGenerator
from generators.pulse import PulseGenerator
from generators.triangle import TriangleGenerator
from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction
from typehints.enums import (
    GeneratorClassName,
    GeneratorName,
    InstructionClassName,
    LibraryGeneratorName,
)
from typehints.exporters import ExporterClass
from typehints.generators import GeneratorClass, GeneratorUnion
from typehints.instructions import InstructionClass, InstructionUnion

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


INSTRUCTION_CLASS_MAP: Dict[InstructionClassName, InstructionClass] = {
    InstructionClassName.TRIANGLE_INSTRUCTION: TriangleInstruction,
    InstructionClassName.PULSE_INSTRUCTION: PulseInstruction,
    InstructionClassName.NOISE_INSTRUCTION: NoiseInstruction,
}


INSTRUCTION_TO_GENERATOR_MAP: Dict[InstructionClass, GeneratorClass] = {
    TriangleInstruction: TriangleGenerator,
    PulseInstruction: PulseGenerator,
    NoiseInstruction: NoiseGenerator,
}


INSTRUCTION_TO_EXPORTER_MAP: Dict[InstructionClass, ExporterClass] = {
    TriangleInstruction: TriangleExporter,
    PulseInstruction: PulseExporter,
    NoiseInstruction: NoiseExporter,
}


MIXER_LEVELS: Dict[GeneratorClassName, float] = {
    GeneratorClassName.PULSE_GENERATOR: MIXER_PULSE,
    GeneratorClassName.NOISE_GENERATOR: MIXER_NOISE,
    GeneratorClassName.TRIANGLE_GENERATOR: MIXER_TRIANGLE,
}


def get_remaining_generator_classes(
    remaining_generators: Dict[str, GeneratorUnion],
) -> Dict[GeneratorClassName, GeneratorUnion]:
    return {generator.class_name(): generator for generator in reversed(remaining_generators.values())}


def get_generator_by_instruction(
    instruction: InstructionUnion, remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion]
) -> GeneratorUnion:
    generator_class = INSTRUCTION_TO_GENERATOR_MAP[type(instruction)].__name__
    generator_class_literal = cast(GeneratorClassName, generator_class)
    return remaining_generator_classes[generator_class_literal]
