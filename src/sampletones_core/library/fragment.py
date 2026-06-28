from __future__ import annotations

from functools import cached_property
from typing import Any, Generic, List, Self

import numpy as np
from pydantic import ConfigDict

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorClassName, SpectrumMethod
from sampletones_core.constants.general import LIBRARY_PHASES_PER_SAMPLE
from sampletones_core.constants.spectrum import (
    CQT_REFERENCE_COLUMNS,
    CQT_REFERENCE_CONTEXT_FACTOR,
)
from sampletones_core.data import DataModel
from sampletones_core.fft import CyclicArray, FFTTransformer, Fragment, Window
from sampletones_core.fft.spectrum.cqt import calculate_cqt_spectrum_columns
from sampletones_core.generators import (
    GENERATOR_CLASS_MAP,
    GENERATOR_TO_INSTRUCTION_MAP,
    Generator,
)
from sampletones_core.instructions import InstructionData, InstructionT
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.exceptions import InstructionTypeMismatchError
from sampletones_shared.types.data import (
    Initials,
    ReducedObject,
    SerializedData,
)


def _instruction_library_fragment(
    data: SerializedData,
) -> InstructionLibraryFragment[Any]:
    return InstructionLibraryFragment(**data)


class InstructionLibraryFragment(DataModel, Generic[InstructionT]):
    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)

    generator_class: GeneratorClassName
    instruction_data: InstructionData[InstructionT]
    sample: CyclicArray
    feature: Histogram
    frequency: float

    def __reduce__(self) -> ReducedObject:
        return (_instruction_library_fragment, (dict(self),))

    @classmethod
    def create(
        cls,
        generator: Generator[InstructionT, Any],
        instruction: InstructionT,
        window: Window,
        transformer: FFTTransformer,
    ) -> Self:
        sample: CyclicArray = generator.generate_sample(instruction)
        feature: Histogram = cls._get_average_feature(sample, window, transformer)

        return cls(
            generator_class=generator.class_name(),
            instruction_data=InstructionData.create(instruction),
            sample=sample,
            feature=feature,
            frequency=generator.timer.real_frequency,
        )

    @cached_property
    def instruction(self) -> InstructionT:
        if not isinstance(
            self.instruction_data.instruction,
            GENERATOR_TO_INSTRUCTION_MAP[GENERATOR_CLASS_MAP[self.generator_class]],
        ):
            raise InstructionTypeMismatchError("Instruction type does not match generator class")

        instruction: InstructionT = self.instruction_data.instruction
        return instruction

    @staticmethod
    def _get_average_feature(
        sample: CyclicArray,
        window: Window,
        transformer: FFTTransformer,
    ) -> Histogram:
        match SpectrumMethod(transformer.spectrum_method):
            case SpectrumMethod.CQT:
                return InstructionLibraryFragment._cqt_steady_state_feature(sample, window, transformer)
            case _:
                return InstructionLibraryFragment._phase_averaged_feature(sample, window, transformer)

    @staticmethod
    def _phase_averaged_feature(
        sample: CyclicArray,
        window: Window,
        transformer: FFTTransformer,
    ) -> Histogram:
        features: List[Histogram] = []
        sample_rate = transformer.sample_rate
        for phase_id in range(LIBRARY_PHASES_PER_SAMPLE):
            phase = phase_id / LIBRARY_PHASES_PER_SAMPLE
            windowed_audio = sample.get_windowed_fragment(phase, window)
            features.append(transformer.calculate_feature(windowed_audio, sample_rate))

        return transformer.mean(features)

    @staticmethod
    def _cqt_steady_state_feature(
        sample: CyclicArray,
        window: Window,
        transformer: FFTTransformer,
    ) -> Histogram:
        """
        Steady-state CQT feature of a candidate, via the same whole-signal transform
        as the matching target.

        The candidate is stationary, so its CQT magnitude is the same in every frame.
        Looping it into a buffer long enough for librosa's centered framing and
        averaging the interior columns yields the column the target CQT would report
        while this candidate plays, which keeps target and reference comparable
        bin-by-bin. Averaging happens in spectrum space before the gamma transform,
        matching how the per-window path averages phases.
        """
        buffer = sample.get_fragment(0, CQT_REFERENCE_CONTEXT_FACTOR * window.size)
        spectra = calculate_cqt_spectrum_columns(buffer, transformer.sample_rate, window.frame_length)
        start = max(0, (len(spectra) - CQT_REFERENCE_COLUMNS) // 2)
        interior = spectra[start : start + CQT_REFERENCE_COLUMNS]
        mean_values = np.mean([histogram.values for histogram in interior], axis=0)
        spectrum = Histogram(edges=interior[0].edges, values=mean_values.astype(np.float32))
        return transformer.forward(spectrum)

    def get_fragment(self, shift: int, config: Config, window: Window) -> Fragment:
        windowed_audio = self.sample.get_windowed_fragment(shift, window)
        audio = window.get_frame_from_window(windowed_audio)
        return Fragment(
            audio=audio,
            feature=self.feature,
            windowed_audio=windowed_audio,
            config=config,
        )

    def get(
        self,
        generator: Generator[InstructionT, Any],
        config: Config,
        window: Window,
        initials: Initials = None,
    ) -> Fragment:
        generator.set_timer(self.instruction)
        shift = generator.timer.calculate_offset(initials)
        return self.get_fragment(shift, config, window)

    @property
    def data(self) -> np.ndarray:
        return self.sample.array

    @property
    def empty(self) -> bool:
        return self.sample.length == 0

    @property
    def length(self) -> int:
        return self.sample.length
