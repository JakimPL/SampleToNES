from typing import Any, Dict, List, Tuple

from sampletones_core.configs import Config, InstructionsLibraryConfig
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import FFTTransformer, Window
from sampletones_core.generators import GeneratorUnion, get_generators_map
from sampletones_core.generators.maps import GENERATOR_CLASS_MAP
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryFragment


def generate_instruction(
    generators: Dict[GeneratorClassName, GeneratorUnion],
    generator_class_name: GeneratorClassName,
    instruction: InstructionUnion,
    window: Window,
    transformer: FFTTransformer,
) -> Tuple[InstructionUnion, InstructionLibraryFragment[Any]]:
    generator = generators[generator_class_name]
    fragment: InstructionLibraryFragment[Any] = InstructionLibraryFragment.create(
        generator,
        instruction,
        window,
        transformer=transformer,
    )
    return instruction, fragment


def generate_instructions(
    instructions_batch: List[Tuple[GeneratorClassName, InstructionUnion]],
    config: InstructionsLibraryConfig,
    window: Window,
    generators: Dict[GeneratorClassName, GeneratorUnion],
) -> List[Tuple[InstructionUnion, InstructionLibraryFragment[Any]]]:
    transformer = FFTTransformer.from_gamma(
        config.transformation_gamma,
        config.sample_rate,
        config.spectrum_method,
    )
    return [
        generate_instruction(generators, generator_class_name, instruction, window, transformer)
        for generator_class_name, instruction in instructions_batch
    ]


def generate_instruction_batch(
    task: Tuple[List[Tuple[GeneratorClassName, InstructionUnion]], Config, Window],
) -> List[Tuple[InstructionUnion, InstructionLibraryFragment[Any]]]:
    instructions_batch, config, window = task

    generators: Dict[GeneratorClassName, GeneratorUnion] = get_generators_map(config)
    return generate_instructions(instructions_batch, config.library, window, generators)


def generate_single_instruction_task(
    task: Tuple[Tuple[GeneratorClassName, InstructionUnion], Config, Window],
) -> Tuple[InstructionUnion, InstructionLibraryFragment[Any]]:
    (generator_class_name, instruction), config, window = task
    generator = GENERATOR_CLASS_MAP[generator_class_name](config, generator_class_name)
    transformer = FFTTransformer.from_gamma(
        config.library.transformation_gamma,
        config.library.sample_rate,
        config.library.spectrum_method,
    )
    fragment: InstructionLibraryFragment[Any] = InstructionLibraryFragment.create(
        generator,
        instruction,
        window,
        transformer=transformer,
    )
    return instruction, fragment
