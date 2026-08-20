from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Final, KeysView, List, Self, Union, ValuesView

from pydantic import ConfigDict, Field, ValidationError

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.upgrade import upgrade_binary
from sampletones_core.configs import Config, InstructionsLibraryConfig
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.data import DataModel, Metadata, MetadataContract
from sampletones_core.generators import GeneratorClassNames
from sampletones_core.instructions import InstructionUnion
from sampletones_shared.application import SAMPLETONES_LIBRARY_DATA_VERSION
from sampletones_shared.exceptions import (
    IncompatibleLibraryDataVersionError,
    InvalidLibraryDataValuesError,
    SampleToNESError,
    UnhandledLibraryError,
)
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_binary

from .fragment import InstructionLibraryFragment
from .item import LibraryItem

LIBRARY_DATA_CONTRACT: Final[MetadataContract] = MetadataContract(
    label="Library data",
    expected_version=SAMPLETONES_LIBRARY_DATA_VERSION,
    error=IncompatibleLibraryDataVersionError,
)


class InstructionLibraryData(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    metadata: Metadata = Field(
        default_factory=Metadata.default,
        description="Library metadata",
    )
    config: InstructionsLibraryConfig = Field(..., description="Configuration of the library data")
    items: List[LibraryItem[InstructionUnion]] = Field(
        ...,
        description="Library data mapping instructions to fragments",
    )

    @cached_property
    def data(self) -> Dict[InstructionUnion, InstructionLibraryFragment[Any]]:
        return {item.instruction: item.fragment for item in self.items}

    @cached_property
    def subdata(
        self,
    ) -> Dict[
        GeneratorClassName,
        Dict[InstructionUnion, InstructionLibraryFragment[Any]],
    ]:
        subdata = {}
        for generator_class_name in GeneratorClassName:
            subdata[generator_class_name] = {
                instruction: fragment
                for instruction, fragment in self.data.items()
                if fragment.generator_class == generator_class_name
            }

        return subdata

    def __getitem__(self, key: InstructionUnion) -> InstructionLibraryFragment[Any]:
        return self.data[key]

    @classmethod
    def create(
        cls,
        config: Union[Config, InstructionsLibraryConfig],
        data: Dict[InstructionUnion, InstructionLibraryFragment[Any]],
    ) -> Self:
        library_config = config.library if isinstance(config, Config) else config
        items = [
            LibraryItem.create(
                instruction=instruction,
                fragment=fragment,
            )
            for instruction, fragment in data.items()
        ]
        return cls(config=library_config, items=items)

    def filter(
        self,
        generator_classes: GeneratorClassNames,
    ) -> Dict[InstructionUnion, InstructionLibraryFragment[Any]]:
        if not generator_classes:
            return {}

        if isinstance(generator_classes, GeneratorClassName):
            return self.subdata.get(generator_classes, {})

        if isinstance(generator_classes, tuple):
            result: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
            for generator_class_name in generator_classes:
                result |= self.subdata[generator_class_name]
            return result

        raise ValueError(
            f"Incorrect type {type(generator_classes)} of generator class provided, "
            f"expected GeneratorClassName or a tuple of GeneratorClassName."
        )

    def keys(self) -> KeysView[InstructionUnion]:
        return self.data.keys()

    def values(self) -> ValuesView[InstructionLibraryFragment[Any]]:
        return self.data.values()

    @classmethod
    def load(cls, path: Pathlike, fast: bool = True) -> InstructionLibraryData:
        binary = load_binary(path)

        try:
            binary = upgrade_binary(ObjectKind.LIBRARY, binary)
            return InstructionLibraryData.deserialize(
                binary,
                validation=cls.validate_metadata,
                fast=fast,
            )
        except (ValidationError, TypeError) as exception:
            raise InvalidLibraryDataValuesError(
                f'Failed to deserialize LibraryData from "{Path(path)}" due to validation error: {exception}',
                exception,
            ) from exception
        except SampleToNESError:
            raise
        except Exception as exception:
            raise UnhandledLibraryError(
                f'Unhandled library error while loading "{Path(path)}": {exception}'
            ) from exception

    @staticmethod
    def validate_metadata(metadata: Metadata) -> None:
        if not isinstance(metadata, Metadata):
            return

        LIBRARY_DATA_CONTRACT.validate(metadata, metadata.library_data_version)
