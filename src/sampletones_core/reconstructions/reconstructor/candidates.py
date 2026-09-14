from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Dict, List, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import (
    GeneratorClassName,
    InstructionClassName,
)
from sampletones_core.fft import Fragment, Window
from sampletones_core.generators import (
    GeneratorUnion,
    get_generator_by_instruction,
)
from sampletones_core.instructions import (
    INSTRUCTION_CLASS_MAP,
    InstructionUnion,
)
from sampletones_core.library import InstructionLibraryData

from .approximation import ExpectedApproximation

SerializedInstructions = Tuple[Tuple[InstructionClassName, bytes], ...]
CachedApproximations = Callable[[SerializedInstructions, Tuple[GeneratorUnion, ...]], Fragment]


@lru_cache(maxsize=16)
def serialize_instructions(
    instructions: Tuple[InstructionUnion, ...],
) -> SerializedInstructions:
    return tuple((instruction.class_name(), instruction.serialize()) for instruction in instructions)


@dataclass(frozen=True)
class CandidateProvider:
    config: Config
    window: Window
    library_data: InstructionLibraryData

    _cached_approximations: CachedApproximations = field(init=False)
    _moments: Dict[InstructionUnion, Tuple[float, float]] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_cached_approximations", self._build_cached_approximations())

    def candidates(
        self,
        remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion],
    ) -> Tuple[Tuple[InstructionUnion, ...], Fragment]:
        valid_instructions = tuple(self.library_data.filter(tuple(remaining_generator_classes)).keys())
        approximations = self._get_approximations(valid_instructions, remaining_generator_classes)
        return valid_instructions, approximations

    def get_approximation(self, instruction: InstructionUnion, generator: GeneratorUnion) -> Fragment:
        library_fragment = self.library_data[instruction]
        fragment = library_fragment.get(
            generator,
            self.config,
            self.window,
            generator.initials,
        )
        return fragment * self.config.generation.drive

    def get_expected_approximation(
        self,
        instruction: InstructionUnion,
        generator: GeneratorUnion,
    ) -> ExpectedApproximation:
        """The candidate's contribution averaged over every phase its library sample holds."""
        mean, variance = self._sample_moments(instruction)
        return ExpectedApproximation(
            rendering=self.get_approximation(instruction, generator),
            feature=self.library_data[instruction].feature,
            mean=mean,
            variance=variance,
            drive=self.config.generation.drive,
        )

    def _sample_moments(self, instruction: InstructionUnion) -> Tuple[float, float]:
        """The mean and the variance of the instruction's library sample, read once per library."""
        moments = self._moments.get(instruction)
        if moments is None:
            sample = self.library_data[instruction].sample
            moments = (sample.mean, sample.variance)
            self._moments[instruction] = moments

        return moments

    def _get_approximations(
        self,
        valid_instructions: Tuple[InstructionUnion, ...],
        remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion],
    ) -> Fragment:
        serialized_instructions = serialize_instructions(valid_instructions)
        remaining_generators = tuple(remaining_generator_classes.values())
        return self._cached_approximations(serialized_instructions, remaining_generators)

    def _build_cached_approximations(self) -> CachedApproximations:
        @lru_cache(maxsize=16)
        def cached(
            serialized_instructions: SerializedInstructions,
            remaining_generators: Tuple[GeneratorUnion, ...],
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

        return cached
