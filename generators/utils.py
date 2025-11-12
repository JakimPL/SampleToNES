from typing import Dict, cast

from constants.enums import GeneratorClassName
from generators.maps import INSTRUCTION_TO_GENERATOR_MAP
from generators.typehints import GeneratorUnion
from instructions.typehints import InstructionUnion


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
