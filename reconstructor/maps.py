from typing import Dict, cast

from constants import MIXER_NOISE, MIXER_PULSE, MIXER_TRIANGLE
from generators.noise import NoiseGenerator
from generators.pulse import PulseGenerator
from generators.triangle import TriangleGenerator
from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction
from typehints.general import GeneratorClassName, InstructionClassName
from typehints.generators import GeneratorClass, GeneratorUnion
from typehints.instructions import InstructionClass, InstructionUnion

GENERATOR_CLASSES: Dict[str, GeneratorClass] = {
    "triangle": TriangleGenerator,
    "noise": NoiseGenerator,
    "pulse1": PulseGenerator,
    "pulse2": PulseGenerator,
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
