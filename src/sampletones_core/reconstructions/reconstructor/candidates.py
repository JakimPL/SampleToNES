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
        powers: One row per candidate: its power density per bin averaged over phase, as its
            library sample plays, on the active array backend.
    """

    instructions: Tuple[InstructionUnion, ...]
    powers: xp.ndarray


@dataclass(frozen=True)
class CandidateProvider:
    """
    Serves the library's candidates in the forms the matching reads them in.

    Every quantity stands at the level the library sample plays, which the matching reads at
    the drive the channel is asked for, so one set of rows serves every drive a run holds. A
    candidate's power is read off its phase-averaged library feature once per library and kept
    per generator class, so every frame mixes the same rows. Its waveform and its moments are
    read where a shortlist asks for them.

    A conversion reading its frames with several spectrum methods (``analysis_layers``) reads each
    candidate in each method's library, so a candidate's power holds every method's bins stacked in
    the order the frame's feature stacks them, the library's own method first. Its waveform and
    moments are the library's own.

    Attributes:
        config: The conversion's configuration.
        window: The analysis window of the library's own method.
        library_data: The library of the library's own method.
        extractor: The extractor of the library's own method, whose transform reads every bin.
        layer_data: The library of each spectrum method the conversion adds, in the order it adds them.
    """

    config: Config
    window: Window
    library_data: InstructionLibraryData
    extractor: FeatureExtractor
    layer_data: Tuple[InstructionLibraryData, ...]

    _cached_powers: CachedPowers = field(init=False)
    _moments: Dict[InstructionUnion, Tuple[float, float]] = field(init=False, default_factory=dict)
    _classes: Dict[Tuple[GeneratorClassName, ...], ClassCandidates] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_cached_powers", self._build_cached_powers())

    @property
    def libraries(self) -> Tuple[InstructionLibraryData, ...]:
        """Every library a candidate is read in, the library's own method first."""
        return (self.library_data, *self.layer_data)

    @cached_property
    def sizes(self) -> Tuple[int, ...]:
        """How many bins each library's feature axis holds, in the order the frame's feature stacks them."""
        return tuple(_axis(data).shape[0] - 1 for data in self.libraries)

    @cached_property
    def widths(self) -> np.ndarray:
        """The width of every bin of the feature axes the libraries are described on, stacked in order."""
        return np.concatenate([np.diff(_axis(data)) for data in self.libraries])

    def candidates(self, generator_classes: Dict[GeneratorClassName, GeneratorUnion]) -> ClassCandidates:
        """Every candidate of ``generator_classes`` with the power its library sample plays at, gathered once."""
        names = tuple(generator_classes)
        gathered = self._classes.get(names)
        if gathered is None:
            instructions = tuple(self.library_data.filter(names).keys())
            gathered = ClassCandidates(
                instructions=instructions, powers=self._cached_powers(serialize_instructions(instructions))
            )
            self._classes[names] = gathered

        return gathered

    def features_of(self, powers: xp.ndarray) -> xp.ndarray:
        """The feature values of power densities, for one row of them or a stack."""
        return self.extractor.transformer.forward(xp.asarray(powers)) * xp.asarray(self.widths)

    def power_of(self, instruction: InstructionUnion) -> np.ndarray:
        """The candidate's power density per bin averaged over phase, as its library sample plays."""
        values = np.concatenate(
            [np.asarray(data[instruction].feature.values, dtype=np.float64) for data in self.libraries]
        )
        return np.asarray(self.extractor.transformer.backward(values / self.widths))

    def library_waveform(self, instruction: InstructionUnion) -> np.ndarray:
        """The frame the candidate's library sample plays from its own start."""
        fragment = self.library_data[instruction].get_fragment(START_OF_SAMPLE, self.config, self.window)
        return np.asarray(fragment.audio, dtype=np.float64)

    def expected_moments(self, instruction: InstructionUnion) -> Tuple[float, float]:
        """The mean level and the per-sample variance of the candidate's library sample, read once per library."""
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


def _axis(library_data: InstructionLibraryData) -> np.ndarray:
    """The bin edges of the feature axis a library describes its candidates on."""
    return np.asarray(next(iter(library_data.values())).feature.edges, dtype=np.float64)
