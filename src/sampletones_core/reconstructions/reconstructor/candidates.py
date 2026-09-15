from dataclasses import dataclass, field
from functools import cached_property, lru_cache
from typing import Callable, Dict, Final, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import (
    GeneratorClassName,
    InstructionClassName,
)
from sampletones_core.fft import Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import (
    INSTRUCTION_CLASS_MAP,
    InstructionUnion,
)
from sampletones_core.library import InstructionLibraryData
from sampletones_shared.array import xp

SerializedInstructions = Tuple[Tuple[InstructionClassName, bytes], ...]
CachedPowers = Callable[[SerializedInstructions], xp.ndarray]
START_OF_SAMPLE: Final[int] = 0


@lru_cache(maxsize=16)
def serialize_instructions(
    instructions: Tuple[InstructionUnion, ...],
) -> SerializedInstructions:
    return tuple((instruction.class_name(), instruction.serialize()) for instruction in instructions)


@dataclass(frozen=True)
class ClassCandidates:
    """
    The candidates of some generator classes, with the power each adds to a frame.

    Attributes:
        instructions: The candidates, in library order.
        powers: One row per candidate: its power density per bin averaged over phase, at the
            drive it plays at, on the active array backend.
    """

    instructions: Tuple[InstructionUnion, ...]
    powers: xp.ndarray


@dataclass(frozen=True)
class CandidateProvider:
    """
    Serves the library's candidates in the forms the matching reads them in.

    A candidate's power is read off its phase-averaged library feature once per library and
    kept per generator class, so every frame mixes the same rows. Its waveform and its moments
    are read where a shortlist asks for them.
    """

    config: Config
    window: Window
    library_data: InstructionLibraryData
    extractor: FeatureExtractor

    _cached_powers: CachedPowers = field(init=False)
    _moments: Dict[InstructionUnion, Tuple[float, float]] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_cached_powers", self._build_cached_powers())

    @property
    def drive(self) -> float:
        return self.config.generation.drive

    @cached_property
    def widths(self) -> np.ndarray:
        """The width of every bin of the feature axis the library is described on."""
        feature = next(iter(self.library_data.values())).feature
        return np.asarray(np.diff(feature.edges), dtype=np.float64)

    def candidates(self, generator_classes: Dict[GeneratorClassName, GeneratorUnion]) -> ClassCandidates:
        """Every candidate of ``generator_classes``, with its power at the configured drive."""
        instructions = tuple(self.library_data.filter(tuple(generator_classes)).keys())
        return ClassCandidates(
            instructions=instructions, powers=self._cached_powers(serialize_instructions(instructions))
        )

    def features_of(self, powers: xp.ndarray) -> xp.ndarray:
        """The feature values of power densities, for one row of them or a stack."""
        return self.extractor.transformer.forward(xp.asarray(powers)) * xp.asarray(self.widths)

    def power_of(self, instruction: InstructionUnion) -> np.ndarray:
        """The candidate's power density per bin averaged over phase, at the configured drive."""
        values = np.asarray(self.library_data[instruction].feature.values, dtype=np.float64)
        return np.asarray(self.extractor.transformer.backward(values / self.widths)) * self.drive**2

    def library_waveform(self, instruction: InstructionUnion) -> np.ndarray:
        """The frame the candidate's library sample plays from its own start, at the configured drive."""
        fragment = self.library_data[instruction].get_fragment(START_OF_SAMPLE, self.config, self.window)
        return np.asarray(fragment.audio, dtype=np.float64) * self.drive

    def expected_moments(self, instruction: InstructionUnion) -> Tuple[float, float]:
        """The mean level and the per-sample variance the candidate renders at, at the configured drive."""
        mean, variance = self._sample_moments(instruction)
        return self.drive * mean, self.drive**2 * variance

    def _sample_moments(self, instruction: InstructionUnion) -> Tuple[float, float]:
        """The mean and the variance of the instruction's library sample, read once per library."""
        moments = self._moments.get(instruction)
        if moments is None:
            sample = self.library_data[instruction].sample
            moments = (sample.mean, sample.variance)
            self._moments[instruction] = moments

        return moments

    def _build_cached_powers(self) -> CachedPowers:
        @lru_cache(maxsize=16)
        def cached(serialized_instructions: SerializedInstructions) -> xp.ndarray:
            rows = [
                self.power_of(INSTRUCTION_CLASS_MAP[class_name].deserialize(serialized))
                for class_name, serialized in serialized_instructions
            ]
            return xp.asarray(np.stack(rows))

        return cached
