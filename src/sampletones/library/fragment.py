from types import ModuleType
from typing import Generic, Self

import numpy as np
from flatbuffers.table import Table
from pydantic import ConfigDict, field_serializer

from sampletones.configs import Config
from sampletones.constants.enums import GeneratorClassName
from sampletones.constants.general import LIBRARY_PHASES_PER_SAMPLE
from sampletones.data import DataModel
from sampletones.ffts import CyclicArray, Fragment, Window
from sampletones.ffts.transformations import FFTTransformer
from sampletones.generators import (
    GENERATOR_CLASS_MAP,
    GENERATOR_TO_INSTRUCTION_MAP,
    GeneratorType,
)
from sampletones.instructions import InstructionType
from sampletones.typehints import Initials, SerializedData
from sampletones.utils import serialize_array


class LibraryFragment(DataModel, Generic[InstructionType, GeneratorType]):
    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)

    generator_class: GeneratorClassName
    instruction: InstructionType
    sample: CyclicArray
    feature: np.ndarray
    frequency: float

    @classmethod
    def create(
        cls,
        generator: GeneratorType,
        instruction: InstructionType,
        window: Window,
        transformer: FFTTransformer,
    ) -> Self:
        sample: CyclicArray = generator.generate_sample(instruction)

        features = []
        for phase_id in range(LIBRARY_PHASES_PER_SAMPLE):
            phase = phase_id / LIBRARY_PHASES_PER_SAMPLE
            windowed_audio = sample.get_window(phase, window)
            transformed_windowed_audio = transformer.calculate(windowed_audio)
            features.append(transformed_windowed_audio)

        feature = transformer.inverse(np.mean(features, axis=0))

        return cls(
            generator_class=generator.class_name(),
            instruction=instruction,
            sample=sample,
            feature=feature,
            frequency=generator.timer.real_frequency,
        )

    def get_fragment(self, shift: int, config: Config, window: Window) -> Fragment:
        windowed_audio = self.sample.get_window(shift, window)
        audio = window.get_frame_from_window(windowed_audio)
        return Fragment(
            audio=audio,
            feature=self.feature,
            windowed_audio=windowed_audio,
            config=config,
        )

    def get(
        self,
        generator: GeneratorType,
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

    @field_serializer("feature")
    def _serialize_feature(self, feature: np.ndarray) -> SerializedData:
        return serialize_array(feature)

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.library.FBLibraryFragment as FBLibraryFragment

        return FBLibraryFragment

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.library.FBLibraryFragment as FBLibraryFragment

        return FBLibraryFragment.FBLibraryFragment

    @classmethod
    def _deserialize_union(cls, table: Table, field_values: SerializedData) -> Self:
        generator_class_name = GeneratorClassName(field_values["generator_class"])
        instruction_class = GENERATOR_TO_INSTRUCTION_MAP[GENERATOR_CLASS_MAP[generator_class_name]]
        return instruction_class._deserialize_from_table(table)
