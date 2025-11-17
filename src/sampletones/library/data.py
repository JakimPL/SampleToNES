from functools import cached_property
from pathlib import Path
from types import ModuleType
from typing import Collection, Dict, Generic, Self, Union

import numpy as np
from flatbuffers.table import Table
from pydantic import ConfigDict, Field, ValidationError

from sampletones.configs import Config, LibraryConfig
from sampletones.constants.application import (
    SAMPLETONES_LIBRARY_DATA_VERSION,
    SAMPLETONES_NAME,
    compare_versions,
)
from sampletones.constants.enums import GeneratorClassName
from sampletones.constants.general import LIBRARY_PHASES_PER_SAMPLE
from sampletones.data import DataModel, Metadata, default_metadata
from sampletones.exceptions import (
    IncompatibleLibraryDataVersionError,
    InvalidLibraryDataValuesError,
)
from sampletones.ffts import CyclicArray, Window
from sampletones.ffts.transformations import FFTTransformer
from sampletones.generators import (
    GENERATOR_CLASS_MAP,
    GENERATOR_TO_INSTRUCTION_MAP,
    GeneratorType,
)
from sampletones.instructions import InstructionType, InstructionUnion
from sampletones.typehints import Initials, SerializedData
from sampletones.utils import load_binary, save_binary

from .fragment import Fragment


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

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.library.FBLibraryFragment as FBLibraryFragment

        return FBLibraryFragment

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.library.FBLibraryFragment as FBLibraryFragment

        return FBLibraryFragment.FBLibraryFragment

    @classmethod
    def deserialize_union(cls, table: Table, field_values: SerializedData) -> Self:
        generator_class_name = GeneratorClassName(field_values["generator_class"])
        instruction_class = GENERATOR_TO_INSTRUCTION_MAP[GENERATOR_CLASS_MAP[generator_class_name]]
        return instruction_class._deserialize_from_table(table)


class LibraryData(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: Metadata = Field(
        default_factory=default_metadata,
        description="Library metadata",
    )
    config: LibraryConfig = Field(..., description="Configuration of the library data")
    data: Dict[InstructionUnion, LibraryFragment] = Field(
        ...,
        description="Library data mapping instructions to fragments",
    )

    @cached_property
    def subdata(self) -> Dict[GeneratorClassName, Dict[InstructionUnion, LibraryFragment]]:
        subdata = {}
        for generator_class_name in GeneratorClassName:
            subdata[generator_class_name] = {
                instruction: fragment
                for instruction, fragment in self.data.items()
                if fragment.generator_class == generator_class_name
            }

        return subdata

    def __getitem__(self, key: InstructionUnion) -> LibraryFragment:
        return self.data[key]

    def filter(
        self, generator_classes: Union[GeneratorClassName, Collection[GeneratorClassName]]
    ) -> Dict[InstructionUnion, LibraryFragment]:
        if not generator_classes:
            return {}

        if isinstance(generator_classes, GeneratorClassName):
            return self.subdata.get(generator_classes, {})
        elif isinstance(generator_classes, Collection):
            result: Dict[InstructionUnion, LibraryFragment] = {}
            for generator_class_name in generator_classes:
                result |= self.subdata[generator_class_name]
            return result

        raise ValueError("Incorrect type of generator class provided")

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()

    def save(self, path: Union[str, Path]) -> None:
        binary = self.serialize()
        save_binary(path, binary)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "LibraryData":
        binary = load_binary(path)

        try:
            library_data = LibraryData.deserialize(binary)
        except ValidationError as exception:
            raise InvalidLibraryDataValuesError(
                f"Failed to deserialize LibraryData from {Path(path)} due to validation error",
                exception,
            ) from exception

        cls.validate_library_data(library_data.metadata)
        return library_data

    @staticmethod
    def validate_library_data(metadata: Metadata) -> None:
        application_metadata = metadata.application_name
        assert application_metadata == SAMPLETONES_NAME, "Metadata application name mismatch."

        library_version = metadata.library_data_version
        if compare_versions(library_version, SAMPLETONES_LIBRARY_DATA_VERSION) != 0:
            raise IncompatibleLibraryDataVersionError(
                f"Library data version mismatch: expected "
                f"{SAMPLETONES_LIBRARY_DATA_VERSION}, got {library_version}.",
                expected_version=SAMPLETONES_LIBRARY_DATA_VERSION,
                actual_version=library_version,
            )

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.library.FBLibraryData as FBLibraryData

        return FBLibraryData

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.library.FBLibraryData as FBLibraryData

        return FBLibraryData.FBLibraryData
