from pathlib import Path
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
from sampletones.typehints import FeatureMap, SerializedData
from sampletones.utils import serialize_array
from sampletones.utils.logger import logger

from .state import ReconstructionState


class Reconstruction(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: Metadata = Field(
        default_factory=default_metadata,
        description="Reconstruction metadata",
    )
    audio_filepath: Path = Field(..., description="Path to the original audio file")
    config: Config = Field(..., description="Configuration used for reconstruction")
    approximation: np.ndarray = Field(..., description="Audio approximation")
    approximations: Dict[GeneratorName, np.ndarray] = Field(..., description="Approximations per generator")
    instructions: Dict[GeneratorName, List[InstructionUnion]] = Field(..., description="Instructions per generator")
    errors: Dict[GeneratorName, List[float]] = Field(..., description="Reconstruction errors per generator")
    coefficient: float = Field(..., description="Normalization coefficient used during reconstruction")

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

    def __repr__(self) -> str:
        return (
            f"Reconstruction(audio_shape={self.approximation.shape}, "
            f"total_error={self.total_error}, "
            f"generators={list(self.instructions.keys())})"
        )

    @classmethod
    def from_results(cls, state: ReconstructionState, config: Config, coefficient: float, path: Path) -> Optional[Self]:
        if any(len(approximation) == 0 for approximation in state.approximations.values()):
            logger.warning(f"Reconstruction for file: {path} is empty")
            return None

        approximations = {name: np.concatenate(state.approximations[name]) for name in state.approximations}
        approximation = np.sum(np.array(list(approximations.values())), axis=0)

        return cls(
            approximation=approximation,
            approximations=approximations,
            instructions=state.instructions,
            errors=state.errors,
            config=config,
            coefficient=coefficient,
            audio_filepath=path,
        )

    def get_generator_approximation(self, generator_name: GeneratorName) -> np.ndarray:
        return self.approximations.get(generator_name, np.array([]))

    def get_generator_instructions(self, generator_name: GeneratorName) -> List[InstructionUnion]:
        return self.instructions.get(generator_name, [])

    @property
    def total_error(self) -> float:
        return sum(sum(errors) for errors in self.errors.values())

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

    @field_serializer("approximations")
    def _serialize_approximations(self, approximations: Dict[str, np.ndarray], _info) -> SerializedData:
        return {name: serialize_array(array) for name, array in approximations.items()}

    @field_serializer("instructions")
    def _serialize_instructions(
        self, instructions: Dict[str, List[InstructionUnion]], _info
    ) -> Dict[str, SerializedData]:
        return {
            name: {
                "instructions": [instruction.model_dump() for instruction in instructions],
                "type": type(instructions[0]).__name__,
            }
            for name, instructions in instructions.items()
            if instructions
        }

    @field_serializer("config")
    def _serialize_config(self, config: Config, _info) -> SerializedData:
        return config.model_dump()

    @field_serializer("audio_filepath")
    def _serialize_audio_filepath(self, audio_filepath: Path, _info) -> str:
        return str(audio_filepath)
