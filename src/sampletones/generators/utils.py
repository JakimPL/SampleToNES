from typing import Dict, cast

from sampletones.constants.enums import GeneratorClassName
from sampletones.instructions import InstructionUnion

from .maps import INSTRUCTION_TO_GENERATOR_MAP
from .typehints import GeneratorUnion


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
