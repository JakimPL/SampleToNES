from __future__ import annotations

from functools import cached_property
from typing import Any, Generic, Self

import numpy as np
from pydantic import ConfigDict

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.data import DataModel
from sampletones_core.fft import CyclicArray, Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
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
        extractor: FeatureExtractor,
    ) -> Self:
        sample: CyclicArray = generator.generate_sample(instruction)
        feature: Histogram = extractor.reference_feature(sample)

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
