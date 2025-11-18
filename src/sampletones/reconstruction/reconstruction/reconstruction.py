from functools import cached_property
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Optional, Self, Union, cast

import numpy as np
from pydantic import ConfigDict, Field, field_serializer

from sampletones.configs import Config
from sampletones.constants.application import (
    SAMPLETONES_NAME,
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
    compare_versions,
)
from sampletones.constants.enums import GeneratorName
from sampletones.data import DataModel, Metadata, default_metadata
from sampletones.exceptions import IncompatibleReconstructionVersionError
from sampletones.exporters import INSTRUCTION_TO_EXPORTER_MAP, ExporterClass
from sampletones.instructions import (
    InstructionClass,
    InstructionUnion,
    get_instruction_by_type,
)
from sampletones.instructions.data import InstructionData
from sampletones.typehints import FeatureMap, SerializedData
from sampletones.utils import serialize_array
from sampletones.utils.logger import logger

from ..reconstructor.state import ReconstructionState
from .approximations import ApproximationsItem
from .errors import Errors
from .instructions import InstructionsItem


class Reconstruction(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    metadata: Metadata = Field(
        default_factory=default_metadata,
        description="Reconstruction metadata",
    )
    audio_filepath: Path = Field(..., description="Path to the original audio file")
    config: Config = Field(..., description="Configuration used for reconstruction")
    approximation: np.ndarray = Field(..., description="Audio approximation")
    approximations_data: List[ApproximationsItem] = Field(..., description="Approximations per generator")
    instructions_data: List[InstructionsItem] = Field(..., description="Instructions per generator")
    errors_data: List[Errors] = Field(..., description="Reconstruction errors per generator")
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

    @cached_property
    def errors(self) -> Dict[GeneratorName, List[float]]:
        return {item.generator_name: list(item.errors) for item in self.errors_data}

    @staticmethod
    def _get_exporter_class(instruction: InstructionUnion) -> ExporterClass:
        instruction_type = cast(InstructionClass, type(instruction))
        return INSTRUCTION_TO_EXPORTER_MAP[instruction_type]

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
        approximations: Dict[GeneratorName, np.ndarray],
        instructions: Dict[GeneratorName, List[InstructionUnion]],
        errors: Dict[GeneratorName, List[float]],
        config: Config,
        coefficient: float,
        audio_filepath: Path,
    ) -> Self:
        approximations_data: List[ApproximationsItem] = [
            ApproximationsItem(generator_name=name, approximation=approximation)
            for name, approximation in approximations.items()
        ]

        instructions_data: List[InstructionsItem] = []
        for generator_name, instructions_list in instructions.items():
            instructions_data.append(
                InstructionsItem(
                    generator_name=generator_name,
                    instructions=[
                        InstructionData(
                            instruction_class=instruction.class_name(),
                            instruction=instruction,
                        )
                        for instruction in instructions_list
                    ],
                )
            )

        errors_data: List[Errors] = []
        for name, errors_list in errors.items():
            total_error = sum(errors_list)
            errors_data.append(
                Errors(
                    generator_name=name,
                    errors=np.array(errors_list, dtype=np.float32),
                    total_error=total_error,
                )
            )

        return cls(
            approximation=approximation,
            approximations_data=approximations_data,
            instructions_data=instructions_data,
            errors_data=errors_data,
            config=config,
            coefficient=coefficient,
            audio_filepath=audio_filepath,
        )

    @classmethod
    def from_state(cls, state: ReconstructionState, config: Config, coefficient: float, path: Path) -> Optional[Self]:
        if any(len(approximation) == 0 for approximation in state.approximations.values()):
            logger.warning(f"Reconstruction for file: {path} is empty")
            return None

        approximations = {name: np.concatenate(state.approximations[name]) for name in state.approximations}
        approximation = np.sum(np.array(list(approximations.values())), axis=0)

        return cls.create(
            approximation=approximation,
            approximations=approximations,
            instructions=state.instructions,
            errors=state.errors,
            config=config,
            coefficient=coefficient,
            audio_filepath=path,
        )

    def get_generator_approximation(self, generator_name: GeneratorName) -> np.ndarray:
        return self.approximations.get(generator_name, np.array([], dtype=np.float32))

    def get_generator_instructions(self, generator_name: GeneratorName) -> List[InstructionUnion]:
        return self.instructions.get(generator_name, [])

    @property
    def total_error(self) -> float:
        return sum(error.total_error for error in self.errors_data)

    @classmethod
    def load_and_validate(cls, path: Union[str, Path]) -> "Reconstruction":
        reconstruction = cls.load(path)
        cls.validate_reconstruction(reconstruction.metadata)
        return reconstruction

    @staticmethod
    def validate_reconstruction(metadata: Metadata) -> None:
        application_metadata = metadata.application_name
        assert application_metadata == SAMPLETONES_NAME, "Metadata application name mismatch."

        reconstruction_version = metadata.reconstruction_data_version
        if compare_versions(reconstruction_version, SAMPLETONES_RECONSTRUCTION_DATA_VERSION) != 0:
            raise IncompatibleReconstructionVersionError(
                f"Reconstruction data version mismatch: expected "
                f"{SAMPLETONES_RECONSTRUCTION_DATA_VERSION}, got {reconstruction_version}.",
                expected_version=SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
                actual_version=reconstruction_version,
            )

    def export(self) -> Dict[GeneratorName, FeatureMap]:
        features = {}
        for name, instructions in self.instructions.items():
            if not instructions:
                continue

            exporter_class = self._get_exporter_class(instructions[0])
            exporter = exporter_class()
            features[name] = exporter(instructions)

        return features

    @field_serializer("approximation")
    def _serialize_approximation(self, approximation: np.ndarray, _info) -> SerializedData:
        return serialize_array(approximation)

    @field_serializer("audio_filepath")
    def _serialize_audio_filepath(self, audio_filepath: Path, _info) -> str:
        return str(audio_filepath)

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.reconstruction.FBReconstruction as FBReconstruction

        return FBReconstruction

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.reconstruction.FBReconstruction as FBReconstruction

        return FBReconstruction.FBReconstruction
