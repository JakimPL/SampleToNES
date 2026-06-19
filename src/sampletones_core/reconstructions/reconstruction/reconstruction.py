from __future__ import annotations

import struct
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Self, Sequence
from uuid import uuid4

import numpy as np
from pydantic import ConfigDict, Field, ValidationError, field_serializer

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.data import DataModel, Metadata
from sampletones_core.exporters import (
    INSTRUCTION_TO_EXPORTER_MAP,
    ExporterTypeUnion,
    ExporterUnion,
    Features,
)
from sampletones_core.instructions import (
    InstructionUnion,
    get_instruction_by_type,
)
from sampletones_shared.constants.application import (
    SAMPLETONES_NAME,
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
    compare_versions,
)
from sampletones_shared.exceptions import (
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionValuesError,
    SampleToNESError,
    UnhandledReconstructionError,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import Callback
from sampletones_shared.types.data import SerializedData
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.arrays import pad
from sampletones_shared.utils.serialization import load_binary, serialize_array

from ..reconstructor.state import ReconstructionState
from .approximations import ApproximationsItem
from .instructions import InstructionsItem


class Reconstruction(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: Metadata = Field(default_factory=Metadata.default, description="Reconstruction metadata")
    id: str = Field(..., description="Unique identifier for the reconstruction")
    audio_filepath: Path = Field(..., description="Path to the original audio file")
    config: Config = Field(..., description="Configuration used for reconstruction", frozen=True)
    approximation: np.ndarray = Field(..., description="Audio approximation")
    approximations_data: List[ApproximationsItem] = Field(..., description="Approximations per generator")
    instructions_data: List[InstructionsItem] = Field(..., description="Instructions per generator")
    coefficient: float = Field(..., description="Normalization coefficient used during reconstruction")

    @cached_property
    def approximations(self) -> Dict[GeneratorName, np.ndarray]:
        return {item.generator_name: item.approximation for item in self.approximations_data}

    @cached_property
    def instructions(self) -> Dict[GeneratorName, List[InstructionUnion]]:
        return {
            item.generator_name: [instruction.instruction for instruction in item.instructions]
            for item in self.instructions_data
        }

    @staticmethod
    def _get_exporter_class(instruction: InstructionUnion) -> ExporterTypeUnion:
        return INSTRUCTION_TO_EXPORTER_MAP[type(instruction)]

    @classmethod
    def _parse_instructions(cls, data: Dict[str, SerializedData]) -> Dict[str, List[InstructionUnion]]:
        parsed_instructions = {}
        for name, instructions_data in data.items():
            instruction_class = get_instruction_by_type(instructions_data["type"])
            parsed_instructions[name] = [
                instruction_class(**instruction) for instruction in instructions_data["instructions"]
            ]

        return parsed_instructions

    @classmethod
    def create(
        cls,
        approximation: np.ndarray,
        approximations: Mapping[GeneratorName, np.ndarray],
        instructions: Mapping[GeneratorName, Sequence[InstructionUnion]],
        config: Config,
        coefficient: float,
        audio_filepath: Path,
    ) -> Self:
        approximation = np.nan_to_num(approximation, nan=0.0)
        approximations_data: List[ApproximationsItem] = [
            ApproximationsItem(generator_name=name, approximation=approximation)
            for name, approximation in approximations.items()
        ]

        instructions_data: List[InstructionsItem] = []
        for generator_name, instructions_list in instructions.items():
            instructions_data.append(
                InstructionsItem.create(
                    generator_name=generator_name,
                    instructions=list(instructions_list),
                )
            )

        return cls(
            id=uuid4().hex,
            approximation=approximation,
            approximations_data=approximations_data,
            instructions_data=instructions_data,
            config=config,
            coefficient=coefficient,
            audio_filepath=audio_filepath,
        )

    @classmethod
    def from_state(
        cls,
        state: ReconstructionState,
        config: Config,
        coefficient: float,
        path: Path,
    ) -> Optional[Self]:
        if any(len(approximation) == 0 for approximation in state.approximations.values()):
            logger.warning(f"Reconstruction for file: {path} is empty")
            return None

        approximations = {name: np.concatenate(state.approximations[name]) for name in state.approximations}
        approximation = np.sum(np.array(list(approximations.values())), axis=0)

        return cls.create(
            approximation=approximation,
            approximations=approximations,
            instructions=state.instructions,
            config=config,
            coefficient=coefficient,
            audio_filepath=path,
        )

    def update_generator_data(
        self,
        generator_name: GeneratorName,
        instructions: List[InstructionUnion],
        partial_approximation: np.ndarray,
    ) -> None:
        partial_approximation = np.trim_zeros(partial_approximation, trim="b")
        trimmed_approximation = np.trim_zeros(self.approximation, trim="b")
        max_length = max(len(trimmed_approximation), len(partial_approximation))

        array = np.zeros(max_length, dtype=np.float32)
        array[: len(partial_approximation)] = partial_approximation

        for item in self.approximations.values():
            item_length = len(np.trim_zeros(item, trim="b"))
            max_length = max(max_length, item_length)

        new_approximations_data: List[ApproximationsItem] = []
        for approximation in self.approximations_data:
            if approximation.generator_name == generator_name:
                array = pad(array, 0, max_length)
                new_approximations_data.append(
                    ApproximationsItem(
                        generator_name=approximation.generator_name,
                        approximation=array,
                    )
                )
            else:
                item_array = pad(approximation.approximation, 0, max_length)
                new_approximations_data.append(
                    ApproximationsItem(
                        generator_name=approximation.generator_name,
                        approximation=item_array,
                    )
                )

        new_instructions_data: List[InstructionsItem] = []
        for instruction in self.instructions_data:
            if instruction.generator_name == generator_name:
                new_instructions_data.append(
                    InstructionsItem.create(
                        generator_name=generator_name,
                        instructions=instructions,
                    )
                )
            else:
                new_instructions_data.append(instruction)

        self.approximations_data = new_approximations_data
        self.instructions_data = new_instructions_data
        self.__dict__.pop("approximations", None)
        self.__dict__.pop("instructions", None)
        approximations = list(self.approximations.values())
        self.approximation = np.sum(np.array(approximations), axis=0)

    def get_generator_approximation(self, generator_name: GeneratorName) -> np.ndarray:
        return self.approximations.get(generator_name, np.array([], dtype=np.float32))

    def get_generator_instructions(self, generator_name: GeneratorName) -> List[InstructionUnion]:
        return self.instructions.get(generator_name, [])

    @classmethod
    def load(cls, path: Pathlike, fast: bool = True) -> Reconstruction:
        binary = load_binary(path)
        return cls.deserialize_data(binary, source=Path(path), validation=cls.validate_metadata, fast=fast)

    @classmethod
    def deserialize_data(
        cls,
        binary: bytes,
        source: Pathlike,
        validation: Optional[Callback] = None,
        fast: bool = True,
    ) -> Reconstruction:
        try:
            return cls.deserialize(binary, validation=validation, fast=fast)
        except (ValidationError, TypeError, ValueError, struct.error, IndexError) as exception:
            raise InvalidReconstructionValuesError(
                f'Failed to deserialize ReconstructionData from "{source}" due to validation error: {exception}',
                exception,
            ) from exception
        except SampleToNESError:
            raise
        except Exception as exception:
            raise UnhandledReconstructionError(
                f'Unhandled reconstruction error while loading "{source}": {exception}'
            ) from exception

    @staticmethod
    def validate_metadata(metadata: Metadata) -> None:
        if not isinstance(metadata, Metadata):
            return

        application_metadata = metadata.application_name
        if application_metadata != SAMPLETONES_NAME:
            raise InvalidMetadataError(
                f"Metadata application name mismatch: expected {SAMPLETONES_NAME}, got {application_metadata}"
            )

        reconstruction_version = metadata.reconstruction_data_version
        if compare_versions(reconstruction_version, SAMPLETONES_RECONSTRUCTION_DATA_VERSION) != 0:
            raise IncompatibleReconstructionVersionError(
                f"Reconstruction data version mismatch: expected "
                f"{SAMPLETONES_RECONSTRUCTION_DATA_VERSION}, got {reconstruction_version}.",
                expected_version=SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
                actual_version=reconstruction_version,
            )

    def _validate_instructions(self, exporter: ExporterUnion, instructions: List[InstructionUnion]) -> None:
        first_instruction: InstructionUnion = instructions[0]
        exporter_class = self._get_exporter_class(instructions[0])
        exporter_instruction_type = exporter.get_instruction_type()
        for instruction in instructions:
            if not isinstance(instruction, type(first_instruction)):
                raise TypeError(f"All instructions must be of the same type for exporter {exporter_class.__name__}")

            if not isinstance(instruction, exporter_instruction_type):
                raise TypeError(
                    f"Instruction type {type(instruction).__name__} is not compatible "
                    f"with exporter {exporter_class.__name__}"
                )

    def export(self) -> Dict[GeneratorName, Features]:
        features: Dict[GeneratorName, Features] = {}
        for name, instructions in self.instructions.items():
            if not instructions:
                continue

            exporter_class = self._get_exporter_class(instructions[0])
            exporter: ExporterUnion = exporter_class()
            self._validate_instructions(exporter, instructions)
            feature: Features = exporter.to_features(instructions)  # type: ignore
            features[name] = feature

        return features

    @field_serializer("approximation")
    def _serialize_approximation(self, approximation: np.ndarray, _info: Any) -> SerializedData:
        return serialize_array(approximation)

    @field_serializer("audio_filepath")
    def _serialize_audio_filepath(self, audio_filepath: Path, _info: Any) -> str:
        return str(audio_filepath)
