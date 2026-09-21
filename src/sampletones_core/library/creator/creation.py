from typing import Any, Dict, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Window
from sampletones_core.fft.features import FeatureExtractor, get_feature_extractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.generators.maps import GENERATOR_CLASS_MAP
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryFragment


def generate_instruction(
    generators: Dict[GeneratorClassName, GeneratorUnion],
    generator_class_name: GeneratorClassName,
    instruction: InstructionUnion,
    extractor: FeatureExtractor,
) -> Tuple[InstructionUnion, InstructionLibraryFragment[Any]]:
    generator = generators[generator_class_name]
    fragment: InstructionLibraryFragment[Any] = InstructionLibraryFragment.create(
        generator,
        instruction,
        extractor,
    )
    return instruction, fragment


def generate_single_instruction_task(
    task: Tuple[Tuple[GeneratorClassName, InstructionUnion], Config, Window],
) -> Tuple[InstructionUnion, InstructionLibraryFragment[Any]]:
    (generator_class_name, instruction), config, window = task
    generator = GENERATOR_CLASS_MAP[generator_class_name](config, generator_class_name)
    extractor = get_feature_extractor(config, window)
    fragment: InstructionLibraryFragment[Any] = InstructionLibraryFragment.create(
        generator,
        instruction,
        extractor,
    )
    return instruction, fragment
