from typing import Dict, List, Tuple

from tqdm.auto import tqdm

from configs.config import Config
from configs.library import LibraryConfig
from constants.enums import GeneratorClassName
from ffts.transformations.transformer import FFTTransformer
from ffts.window import Window
from generators.maps import GENERATOR_CLASS_MAP
from generators.typehints import GeneratorUnion
from instructions.typehints import InstructionUnion

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
        for generator_class_name, instruction in tqdm(instructions_batch)
    ]


def generate_instruction_batch(
    task: Tuple[List[Tuple[GeneratorClassName, InstructionUnion]], Config, Window],
) -> List[Tuple[InstructionUnion, LibraryFragment]]:
    instructions_batch, config, window = task

    generators: Dict[GeneratorClassName, GeneratorUnion] = {
        name: GENERATOR_CLASS_MAP[name](config, name) for name in GENERATOR_CLASS_MAP
    }

    return generate_instructions(instructions_batch, config.library, window, generators)
