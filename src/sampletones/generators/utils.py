from typing import Dict, List, cast

from sampletones.configs import Config
from sampletones.constants.enums import GeneratorClassName, GeneratorName
from sampletones.instructions import InstructionUnion

from .maps import GENERATOR_CLASS_MAP, GENERATOR_CLASSES, INSTRUCTION_TO_GENERATOR_MAP
from .typehints import GeneratorUnion


def get_generators_by_names(
    config: Config,
    generator_names: List[GeneratorName],
) -> Dict[GeneratorName, GeneratorUnion]:
    names = generator_names.copy()
    if GeneratorName.PULSE2 in names and not GeneratorName.PULSE1 in names:
        names.remove(GeneratorName.PULSE2)
        names.insert(0, GeneratorName.PULSE1)

    return {name: GENERATOR_CLASSES[name](config, name) for name in names}


def get_generators_map(config: Config) -> Dict[GeneratorClassName, GeneratorUnion]:
    return {name: GENERATOR_CLASS_MAP[name](config, name) for name in GENERATOR_CLASS_MAP}


def get_remaining_generator_classes(
    remaining_generators: Dict[str, GeneratorUnion],
) -> Dict[GeneratorClassName, GeneratorUnion]:
    return {generator.class_name(): generator for generator in reversed(remaining_generators.values())}


def get_generator_by_instruction(
    instruction: InstructionUnion,
    remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion],
) -> GeneratorUnion:
    generator_class = INSTRUCTION_TO_GENERATOR_MAP[type(instruction)].__name__
    generator_class_literal = cast(GeneratorClassName, generator_class)
    return remaining_generator_classes[generator_class_literal]
