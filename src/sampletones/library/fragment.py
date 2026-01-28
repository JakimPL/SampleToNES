from __future__ import annotations

from functools import cached_property
from typing import Any, Generic, List, Self, Type

import numpy as np
from pydantic import ConfigDict

from sampletones.configs import Config
from sampletones.constants.enums import GeneratorClassName
from sampletones.constants.general import LIBRARY_PHASES_PER_SAMPLE
from sampletones.data import DataModel, FlatBufferBuilderProtocol, FlatBufferReaderProtocol
from sampletones.exceptions import InstructionTypeMismatchError
from sampletones.fft import CyclicArray, FFTTransformer, Fragment, Window
from sampletones.generators import GENERATOR_CLASS_MAP, GENERATOR_TO_INSTRUCTION_MAP, Generator
from sampletones.instructions import InstructionData, InstructionT
from sampletones.structures.histogram import Histogram
from sampletones.types.data import Initials, ReducedObject, SerializedData


def _instruction_library_fragment(data: SerializedData) -> InstructionLibraryFragment[Any]:
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
        features: List[Histogram] = []
        sample_rate = transformer.sample_rate
        for phase_id in range(LIBRARY_PHASES_PER_SAMPLE):
            phase = phase_id / LIBRARY_PHASES_PER_SAMPLE
            windowed_audio = sample.get_windowed_fragment(phase, window)
            feature = transformer.calculate_feature(windowed_audio, sample_rate)
            features.append(feature)

        return transformer.mean(features)

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

    @classmethod
    def buffer_builder(cls) -> FlatBufferBuilderProtocol:
        from sampletones_schemas.library import FBInstructionsLibraryFragment

        return FBInstructionsLibraryFragment

    @classmethod
    def buffer_reader(cls) -> Type[FlatBufferReaderProtocol]:
        from sampletones_schemas.library import FBInstructionsLibraryFragment

        return FBInstructionsLibraryFragment.FBInstructionsLibraryFragment
