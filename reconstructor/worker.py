from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from tqdm.auto import tqdm

from config import Config
from ffts.window import Window
from library.fragment import Fragment, FragmentedAudio
from library.library import LibraryData
from reconstructor.approximation import ApproximationData
from reconstructor.criterion import Criterion
from reconstructor.maps import get_generator_by_instruction
from typehints.general import GeneratorClassName
from typehints.instructions import InstructionUnion


@dataclass(frozen=True)
class ReconstructorWorker:
    config: Config
    window: Window
    generators: Dict[str, Any]
    library_data: LibraryData

    criterion: Criterion = field(init=False)

    def __call__(
        self, fragmented_audio: FragmentedAudio, fragment_ids: List[int], show_progress: bool = False
    ) -> Dict[int, Dict[str, ApproximationData]]:
        return {
            fragment_id: self.reconstruct(fragmented_audio[fragment_id])
            for fragment_id in tqdm(fragment_ids, disable=not show_progress)
        }

    def __post_init__(self):
        object.__setattr__(self, "criterion", Criterion(self.config, self.window))

    def get_remaining_generators(self) -> Dict[str, Any]:
        return {name: generator for name, generator in self.generators.items()}

    def reconstruct(self, fragment: Fragment) -> Dict[str, ApproximationData]:
        approximations: Dict[str, ApproximationData] = {}
        remaining_generators = self.get_remaining_generators()
        while remaining_generators:
            remaining_generator_classes = {
                generator.class_name(): generator for generator in reversed(remaining_generators.values())
            }

            fragment_approximation = self.find_best_approximation(fragment, remaining_generator_classes)
            fragment -= fragment_approximation.approximation
            approximations[fragment_approximation.generator_name] = fragment_approximation

            del remaining_generators[fragment_approximation.generator_name]

        return approximations

    def find_best_instruction(
        self,
        fragment: Fragment,
        remaining_generator_classes: Dict[GeneratorClassName, Any],
    ) -> Tuple[InstructionUnion, float]:
        valid_instructions = list(self.library_data.filter(remaining_generator_classes))
        errors = []
        for instruction in valid_instructions:
            generator = get_generator_by_instruction(instruction, remaining_generator_classes)
            approximation = self.get_approximation(instruction, generator)
            error = self.criterion(fragment, approximation, instruction, generator.previous_instruction)
            errors.append(error)

        index = int(np.argmin(errors))
        error = float(errors[index])
        instruction = valid_instructions[index]
        return instruction, error

    def find_best_phase(self, fragment: Fragment, instruction: InstructionUnion) -> Fragment:
        library_fragment = self.library_data[instruction]
        start = library_fragment.offset
        length = library_fragment.sample.shape[0] // 3
        end = start + length

        array = library_fragment.sample[start:end] * self.config.mixer
        windows = sliding_window_view(array, self.config.frame_length)
        remainder = fragment.audio - windows

        rmse = np.sqrt((remainder**2).mean(axis=1))
        best_shift = int(np.argmin(rmse))
        return library_fragment.get_fragment(best_shift, self.window, self.config.fast_log_arfft)

    def find_best_approximation(
        self,
        fragment: Fragment,
        remaining_generator_classes: Dict[GeneratorClassName, Any],
    ) -> Tuple[Fragment, ApproximationData]:
        instruction, error = self.find_best_instruction(fragment, remaining_generator_classes)
        generator = get_generator_by_instruction(instruction, remaining_generator_classes)

        if self.config.find_best_phase:
            approximation = self.find_best_phase(fragment, instruction)
        else:
            approximation = self.get_approximation(instruction, generator)

        return ApproximationData(
            generator_name=generator.name,
            approximation=approximation,
            instruction=instruction,
            error=error,
        )

    def get_approximation(self, instruction: InstructionUnion, generator: Any) -> Fragment:
        library_fragment = self.library_data[instruction]
        fragment = library_fragment.get(
            generator,
            self.window,
            self.config.fast_log_arfft,
            generator.initials,
        )
        return fragment * self.config.mixer
