from typing import Dict, List, Optional, Tuple, cast

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from tqdm.auto import tqdm

from config import Config
from constants import MIXER_NOISE, MIXER_PULSE, MIXER_TRIANGLE
from ffts.window import Window
from generators.noise import NoiseGenerator
from generators.pulse import PulseGenerator
from generators.triangle import TriangleGenerator
from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction
from library.fragment import Fragment, FragmentedAudio
from library.library import Library, LibraryData
from reconstructor.approximation import FragmentApproximation
from reconstructor.criterion import Criterion
from reconstructor.reconstruction import Reconstruction
from reconstructor.state import ReconstructionState
from typehints.general import GeneratorClassName
from typehints.generators import GeneratorClass, GeneratorUnion
from typehints.instructions import InstructionClass, InstructionUnion

GENERATOR_CLASSES: Dict[str, GeneratorClass] = {
    "triangle": TriangleGenerator,
    "noise": NoiseGenerator,
    "pulse1": PulseGenerator,
    "pulse2": PulseGenerator,
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

FIND_BEST_PHASE = True


class Reconstructor:
    def __init__(self, config: Config, generator_names: Optional[List[str]] = None) -> None:
        self.config: Config = config
        self.state: ReconstructionState = ReconstructionState.create([])

        default_generators = list(GENERATOR_CLASSES.keys())
        generator_names = generator_names or default_generators
        self.generators: Dict[str, GeneratorUnion] = {
            name: GENERATOR_CLASSES[name](config, name) for name in generator_names
        }

        self.window: Window = Window(config)
        self.criterion: Criterion = Criterion(config, self.window)

        self.library: LibraryData = self.load_library()

    def __call__(self, audio: np.ndarray) -> Reconstruction:
        self.reset_generators()
        self.state = ReconstructionState.create(list(self.generators.keys()))
        coefficient = np.max(np.abs(audio)) / sum(
            MIXER_LEVELS[generator.class_name()] for generator in self.generators.values()
        )

        fragments = self.get_fragments(audio / coefficient)
        self.reconstruct(fragments)
        return Reconstruction.from_results(self.state, self.config)

    def get_approximation(self, instruction: InstructionUnion, generator: GeneratorUnion) -> Fragment:
        library_fragment = self.library[instruction]
        fragment = library_fragment.get(generator, self.window, generator.initials)
        return fragment * self.config.mixer

    def load_library(self) -> LibraryData:
        library = Library.load()
        return library.get(self.config, self.window)

    def get_fragments(self, audio: np.ndarray) -> FragmentedAudio:
        return FragmentedAudio.create(audio, self.window)

    def get_remaining_generators(self) -> Dict[str, GeneratorUnion]:
        return {name: generator for name, generator in self.generators.items()}

    def get_remaining_generator_classes(
        self, remaining_generators: Optional[Dict[str, GeneratorUnion]] = None
    ) -> Dict[GeneratorClassName, GeneratorUnion]:
        remaining_generators = remaining_generators or self.get_remaining_generators()
        return {generator.class_name(): generator for generator in reversed(remaining_generators.values())}

    def get_generator_by_instruction(
        self,
        instruction: InstructionUnion,
        remaining_generator_classes: Optional[Dict[GeneratorClassName, GeneratorUnion]] = None,
    ) -> GeneratorUnion:
        remaining_generator_classes = remaining_generator_classes or self.get_remaining_generator_classes()
        generator_class = INSTRUCTION_TO_GENERATOR_MAP[type(instruction)].__name__
        generator_class_literal = cast(GeneratorClassName, generator_class)
        return remaining_generator_classes[generator_class_literal]

    def reconstruct(self, fragments: FragmentedAudio) -> None:
        for fragment_id in tqdm(range(len(fragments))):
            remaining_generators = self.get_remaining_generators()
            while remaining_generators:
                for name in self.generators:
                    if name not in remaining_generators:
                        continue

                    remaining_generator_classes = {
                        generator.class_name(): generator for generator in reversed(remaining_generators.values())
                    }

                    fragment = fragments[fragment_id]
                    approximation, fragment_approximation = self.find_best_approximation(
                        fragment, remaining_generator_classes
                    )
                    self.update_state(fragment_approximation)
                    fragments[fragment_id] -= approximation

                    del remaining_generators[fragment_approximation.generator_name]

    def find_best_phase(self, fragment: Fragment, instruction: InstructionUnion) -> Fragment:
        library_fragment = self.library[instruction]
        start = library_fragment.offset
        length = library_fragment.sample.shape[0] // 3
        end = start + length
        array = library_fragment.sample[start:end]
        windows = sliding_window_view(array, self.config.frame_length)
        remainder = fragment.audio - windows
        rmse = np.sqrt((remainder**2).mean(axis=1))
        best_shift = int(np.argmin(rmse))
        return library_fragment.get_fragment(best_shift, self.window)

    def find_best_instruction(
        self, fragment: Fragment, remaining_generator_classes: Optional[Dict[GeneratorClassName, GeneratorUnion]] = None
    ) -> Tuple[InstructionUnion, float]:
        remaining_generator_classes = remaining_generator_classes or self.get_remaining_generator_classes()
        valid_instructions = list(self.library.filter(remaining_generator_classes))
        errors = []
        for instruction in tqdm(valid_instructions, leave=False):
            generator = self.get_generator_by_instruction(instruction, remaining_generator_classes)
            approximation = self.get_approximation(instruction, generator)
            error = self.criterion(fragment, approximation, instruction, generator.previous_instruction)
            errors.append(error)

        index = int(np.argmin(errors))
        error = float(errors[index])
        instruction = valid_instructions[index]
        return instruction, error

    def find_best_approximation(
        self, fragment: Fragment, remaining_generator_classes: Optional[Dict[GeneratorClassName, GeneratorUnion]] = None
    ) -> Tuple[Fragment, FragmentApproximation]:
        if remaining_generator_classes is None:
            remaining_generator_classes = {generator.class_name(): generator for generator in self.generators.values()}

        instruction, error = self.find_best_instruction(fragment, remaining_generator_classes)
        generator = self.get_generator_by_instruction(instruction, remaining_generator_classes)
        if FIND_BEST_PHASE:
            approximation = self.find_best_phase(fragment, instruction)
        else:
            approximation = self.get_approximation(instruction, generator)

        approximation *= self.config.mixer
        initials = generator.initials

        windowed_audio = generator.generate_window(instruction, self.window, initials)
        real_approximation = Fragment.create(windowed_audio, self.window) * self.config.mixer
        generator(instruction, initials, save=True)

        return approximation, FragmentApproximation(
            generator_name=generator.name,
            fragment=real_approximation,
            instruction=instruction,
            initials=initials,
            terminals=generator.initials,
            error=error,
        )

    def update_state(self, fragment_approximation: FragmentApproximation) -> None:
        self.state.append(fragment_approximation)

    def reset_generators(self) -> None:
        for generator in self.generators.values():
            generator.reset()
