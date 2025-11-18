from functools import cached_property
from pathlib import Path
from types import ModuleType
from typing import Collection, Dict, List, Self, Union

from pydantic import ConfigDict, Field, ValidationError

from sampletones.configs import Config, LibraryConfig
from sampletones.constants.application import (
    SAMPLETONES_LIBRARY_DATA_VERSION,
    SAMPLETONES_NAME,
    compare_versions,
)
from sampletones.constants.enums import GeneratorClassName
from sampletones.data import DataModel, Metadata, default_metadata
from sampletones.exceptions import (
    IncompatibleLibraryDataVersionError,
    InvalidLibraryDataValuesError,
    InvalidMetadataError,
)
from sampletones.instructions import InstructionUnion
from sampletones.utils import load_binary

from .fragment import LibraryFragment
from .item import LibraryItem


class LibraryData(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    metadata: Metadata = Field(
        default_factory=default_metadata,
        description="Library metadata",
    )
    config: LibraryConfig = Field(..., description="Configuration of the library data")
    items: List[LibraryItem] = Field(
        ...,
        description="Library data mapping instructions to fragments",
    )

    @cached_property
    def data(self) -> Dict[InstructionUnion, LibraryFragment]:
        return {item.instruction: item.fragment for item in self.items}

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

    @classmethod
    def create(cls, config: Union[Config, LibraryConfig], data: Dict[InstructionUnion, LibraryFragment]) -> Self:
        library_config = config.library if isinstance(config, Config) else config
        items = [
            LibraryItem(
                instruction_class=instruction.class_name(),
                instruction=instruction,
                fragment=fragment,
            )
            for instruction, fragment in data.items()
        ]
        return cls(config=library_config, items=items)

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

    def values(self):
        return self.data.values()

    @classmethod
    def load(cls, path: Union[str, Path]) -> "LibraryData":
        binary = load_binary(path)

        try:
            library_data = LibraryData.deserialize(binary)
        except (ValidationError, TypeError) as exception:
            raise InvalidLibraryDataValuesError(
                f"Failed to deserialize LibraryData from {Path(path)} due to validation error",
                exception,
            ) from exception

        cls.validate_library_data(library_data.metadata)
        return library_data

    @staticmethod
    def validate_library_data(metadata: Metadata) -> None:
        application_metadata = metadata.application_name
        if application_metadata != SAMPLETONES_NAME:
            raise InvalidMetadataError(
                f"Metadata application name mismatch: expected " f"{SAMPLETONES_NAME}, got {application_metadata}."
            )

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
