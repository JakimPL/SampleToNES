from typing import Dict, cast

from constants.general import MIXER_NOISE, MIXER_PULSE, MIXER_TRIANGLE
from generators.noise import NoiseGenerator
from generators.pulse import PulseGenerator
from generators.triangle import TriangleGenerator
from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction
from typehints.general import GeneratorClassName, GeneratorName, InstructionClassName, LibraryGeneratorName
from typehints.generators import GeneratorClass, GeneratorUnion
from typehints.instructions import InstructionClass, InstructionUnion

LIBRARY_GENERATOR_CLASS_MAP: Dict[LibraryGeneratorName, GeneratorClassName] = {
    "pulse": "PulseGenerator",
    "triangle": "TriangleGenerator",
    "noise": "NoiseGenerator",
}

GENERATOR_CLASSES: Dict[GeneratorName, GeneratorClass] = {
    "pulse1": PulseGenerator,
    "pulse2": PulseGenerator,
    "triangle": TriangleGenerator,
    "noise": NoiseGenerator,
}


GENERATOR_CLASS_MAP: Dict[GeneratorClassName, GeneratorClass] = {
    "PulseGenerator": PulseGenerator,
    "TriangleGenerator": TriangleGenerator,
    "NoiseGenerator": NoiseGenerator,
}


INSTRUCTION_CLASS_MAP: Dict[InstructionClassName, InstructionClass] = {
    "TriangleInstruction": TriangleInstruction,
    "PulseInstruction": PulseInstruction,
    "NoiseInstruction": NoiseInstruction,
}


INSTRUCTION_TO_GENERATOR_MAP: Dict[InstructionClass, GeneratorClass] = {
    TriangleInstruction: TriangleGenerator,
    PulseInstruction: PulseGenerator,
    NoiseInstruction: NoiseGenerator,
}

MIXER_LEVELS: Dict[GeneratorClassName, float] = {
    "PulseGenerator": MIXER_PULSE,
    "NoiseGenerator": MIXER_NOISE,
    "TriangleGenerator": MIXER_TRIANGLE,
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
