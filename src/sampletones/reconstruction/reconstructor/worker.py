from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable, Dict, List, Tuple

CUPY_AVAILABLE = False
try:
    import cupy as xp

    CUPY_AVAILABLE = True
except ImportError:
    import numpy as xp

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from sampletones.configs import Config
from sampletones.constants.enums import (
    GeneratorClassName,
    GeneratorName,
    InstructionClassName,
)
from sampletones.ffts import Fragment, FragmentedAudio, Window
from sampletones.generators import GeneratorUnion, get_generator_by_instruction
from sampletones.instructions import INSTRUCTION_CLASS_MAP, InstructionUnion
from sampletones.library import LibraryData

from ..criterion import Criterion
from .approximation import ApproximationData

GetCachedApproximationsInstructionsArgument = Tuple[Tuple[InstructionClassName, bytes], ...]
GetCachedApproximationsGeneratorsArgument = Tuple[GeneratorUnion, ...]
GetCachedApproximationsCallable = Callable[
    [GetCachedApproximationsInstructionsArgument, GetCachedApproximationsGeneratorsArgument], Fragment
]


@dataclass(frozen=True)
class ReconstructorWorker:
    config: Config
    window: Window
    generators: Dict[GeneratorName, GeneratorUnion]
    library_data: LibraryData

    criterion: Criterion = field(init=False)
    _get_cached_approximations: GetCachedApproximationsCallable = field(init=False)

    def __call__(
        self,
        fragmented_audio: FragmentedAudio,
        fragment_ids: List[int],
    ) -> Dict[int, Dict[GeneratorName, ApproximationData]]:
        return {fragment_id: self.reconstruct(fragmented_audio[fragment_id]) for fragment_id in fragment_ids}

    def __post_init__(self):
        object.__setattr__(self, "criterion", Criterion(self.config, self.window))

        def _build_get_cached_approximations() -> GetCachedApproximationsCallable:
            @lru_cache(maxsize=16)
            def _cached(
                serialized_instructions: Tuple[Tuple[InstructionClassName, bytes], ...],
                remaining_generators: Tuple[GeneratorUnion],
            ) -> Fragment:
                remaining_generator_classes = dict(
                    zip(
                        (generator.class_name() for generator in remaining_generators),
                        remaining_generators,
                    )
                )
                approximations: List[Fragment] = []
                for instruction_class_name, serialized_instruction in serialized_instructions:
                    instruction_class = INSTRUCTION_CLASS_MAP[instruction_class_name]
                    instruction = instruction_class.deserialize(serialized_instruction)
                    generator = get_generator_by_instruction(instruction, remaining_generator_classes)
                    approximation = self.get_approximation(instruction, generator)
                    approximations.append(approximation)

                return Fragment.stack(approximations).to_cupy()

            return _cached

        object.__setattr__(self, "_get_cached_approximations", _build_get_cached_approximations())

    def get_remaining_generators(self) -> Dict[GeneratorName, GeneratorUnion]:
        return {name: generator for name, generator in self.generators.items()}

    def get_remaining_generator_classes(
        self,
        remaining_generators: Dict[GeneratorName, GeneratorUnion],
    ) -> Dict[GeneratorClassName, GeneratorUnion]:
        return {generator.class_name(): generator for generator in reversed(remaining_generators.values())}

    def reconstruct(self, fragment: Fragment) -> Dict[GeneratorName, ApproximationData]:
        approximations: Dict[GeneratorName, ApproximationData] = {}
        remaining_generators = self.get_remaining_generators()
        while remaining_generators:
            remaining_generator_classes = self.get_remaining_generator_classes(remaining_generators)
            fragment_approximation = self.find_best_approximation(fragment, remaining_generator_classes)
            fragment -= fragment_approximation.approximation
            approximations[fragment_approximation.generator_name] = fragment_approximation
            del remaining_generators[fragment_approximation.generator_name]

        return approximations

    def find_best_instruction(
        self,
        fragment: Fragment,
        remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion],
    ) -> Tuple[InstructionUnion, float]:
        valid_instructions = tuple(self.library_data.filter(tuple(remaining_generator_classes)).keys())
        approximations = self.get_approximations(
            valid_instructions,
            remaining_generator_classes,
        )

        errors = None
        fragment_gpu = None
        try:
            fragment_gpu = fragment.to_cupy()
            errors = self.criterion(fragment_gpu, approximations)
            index = int(np.argmin(errors))
            error = float(errors[index])
            instruction = valid_instructions[index]
        finally:
            del errors, approximations, fragment_gpu
            if CUPY_AVAILABLE:
                import cupy

                cupy.get_default_memory_pool().free_all_blocks()

        return instruction, error

    def find_best_phase(self, fragment: Fragment, instruction: InstructionUnion) -> Fragment:
        library_fragment = self.library_data[instruction]
        array = library_fragment.sample.get_fragment(length=2 * library_fragment.sample.length)

        windows = sliding_window_view(array, self.config.library.frame_length)
        remainder = fragment.audio - windows

        rmse = np.sqrt((remainder**2).mean(axis=1))
        best_shift = int(np.argmin(rmse))
        return library_fragment.get_fragment(best_shift, self.config, self.window)

    def find_best_approximation(
        self,
        fragment: Fragment,
        remaining_generator_classes: Dict[GeneratorClassName, Any],
    ) -> ApproximationData:
        instruction, error = self.find_best_instruction(fragment, remaining_generator_classes)
        generator = get_generator_by_instruction(instruction, remaining_generator_classes)

        if self.config.generation.calculation.find_best_phase:
            approximation = self.find_best_phase(fragment, instruction)
        else:
            approximation = self.get_approximation(instruction, generator)

        return ApproximationData(
            generator_name=GeneratorName(generator.name),
            approximation=approximation,
            instruction=instruction,
            error=error,
        )

    def get_approximation(self, instruction: InstructionUnion, generator: GeneratorUnion) -> Fragment:
        library_fragment = self.library_data[instruction]
        fragment = library_fragment.get(
            generator,
            self.config,
            self.window,
            generator.initials,
        )
        return fragment * self.config.generation.mixer

    def get_approximations(
        self,
        valid_instructions: Tuple[InstructionUnion, ...],
        remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion],
    ) -> Fragment:
        serialized_instructions = self._serialize_instructions(valid_instructions)
        remaining_generators = tuple(remaining_generator_classes.values())

        return self._get_cached_approximations(
            serialized_instructions,
            remaining_generators,
        )

    @staticmethod
    @lru_cache(maxsize=16)
    def _serialize_instructions(
        instructions: Tuple[InstructionUnion, ...],
    ) -> GetCachedApproximationsInstructionsArgument:
        return tuple((instruction.class_name(), instruction.serialize()) for instruction in instructions)
