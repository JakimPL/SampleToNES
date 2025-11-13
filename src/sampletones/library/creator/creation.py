from typing import Dict, List, Tuple

from sampletones.configs import Config, LibraryConfig
from sampletones.constants.enums import GeneratorClassName
from sampletones.ffts import Window
from sampletones.ffts.transformations import FFTTransformer
from sampletones.generators import GENERATOR_CLASS_MAP, GeneratorUnion
from sampletones.instructions import InstructionUnion

from ..data import LibraryFragment


def generate_instruction(
    generators: Dict[GeneratorClassName, GeneratorUnion],
    generator_class_name: GeneratorClassName,
    instruction: InstructionUnion,
    window: Window,
    transformer: FFTTransformer,
):
    generator = generators[generator_class_name]
    fragment = LibraryFragment.create(generator, instruction, window, transformer=transformer)
    return instruction, fragment


def generate_instructions(
    instructions_batch: List[Tuple[GeneratorClassName, InstructionUnion]],
    config: LibraryConfig,
    window: Window,
    generators: Dict[GeneratorClassName, GeneratorUnion],
) -> List[Tuple[InstructionUnion, LibraryFragment]]:
    transformer = FFTTransformer.from_gamma(config.transformation_gamma)
    return [
        generate_instruction(generators, generator_class_name, instruction, window, transformer)
        for generator_class_name, instruction in instructions_batch
    ]


def generate_instruction_batch(
    task: Tuple[List[Tuple[GeneratorClassName, InstructionUnion]], Config, Window],
) -> List[Tuple[InstructionUnion, LibraryFragment]]:
    instructions_batch, config, window = task

    generators: Dict[GeneratorClassName, GeneratorUnion] = {
        name: GENERATOR_CLASS_MAP[name](config, name) for name in GENERATOR_CLASS_MAP
    }

    return generate_instructions(instructions_batch, config.library, window, generators)
