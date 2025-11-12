from pathlib import Path
from typing import Any, Dict, List, Optional, Self, Union, cast

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_serializer

from configs.config import Config
from constants.enums import FeatureKey, GeneratorName, InstructionClassName
from constants.general import SAMPLE_TO_NES_NAME, SAMPLE_TO_NES_VERSION
from exceptions.reconstruction import InvalidReconstructionError
from reconstructor.maps import INSTRUCTION_CLASS_MAP, INSTRUCTION_TO_EXPORTER_MAP
from reconstructor.state import ReconstructionState
from typehints.exporters import ExporterClass
from typehints.general import FeatureValue
from typehints.instructions import InstructionClass, InstructionUnion
from utils.logger import logger
from utils.serialization import (
    SerializedData,
    deserialize_array,
    load_json,
    save_json,
    serialize_array,
)


def default_metadata() -> SerializedData:
    return {
        SAMPLE_TO_NES_NAME: {
            "version": SAMPLE_TO_NES_VERSION,
        }
    }


class Reconstruction(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    approximation: np.ndarray = Field(..., description="Audio approximation")
    approximations: Dict[GeneratorName, np.ndarray] = Field(..., description="Approximations per generator")
    instructions: Dict[GeneratorName, List[InstructionUnion]] = Field(..., description="Instructions per generator")
    errors: Dict[GeneratorName, List[float]] = Field(..., description="Reconstruction errors per generator")
    config: Config = Field(..., description="Configuration used for reconstruction")
    coefficient: float = Field(..., description="Normalization coefficient used during reconstruction")
    audio_filepath: Path = Field(..., description="Path to the original audio file")
    metadata: SerializedData = Field(default_factory=default_metadata, description="Additional metadata")

    @staticmethod
    def _get_instruction_class(name: InstructionClassName) -> InstructionClass:
        return INSTRUCTION_CLASS_MAP[name]

    @staticmethod
    def _get_exporter_class(instruction: InstructionUnion) -> ExporterClass:
        instruction_type = cast(InstructionClass, type(instruction))
        return INSTRUCTION_TO_EXPORTER_MAP[instruction_type]

    @classmethod
    def _parse_instructions(cls, data: Dict[str, SerializedData]) -> Dict[str, List[InstructionUnion]]:
        parsed_instructions = {}
        for name, instructions_data in data.items():
            instruction_class = cls._get_instruction_class(instructions_data["type"])
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

    def save(self, filepath: Union[str, Path]) -> None:
        data = self.model_dump()
        save_json(filepath, data)

    @property
    def total_error(self) -> float:
        return sum(sum(errors) for errors in self.errors.values())

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> Self:
        data = load_json(filepath)
        cls.validate_json(data)

        data["approximation"] = deserialize_array(data["approximation"])
        data["approximations"] = {name: deserialize_array(array) for name, array in data["approximations"].items()}
        data["instructions"] = cls._parse_instructions(data["instructions"])
        data["config"] = Config(**data["config"])
        data["coefficient"] = float(data["coefficient"])
        data["audio_filepath"] = Path(data["audio_filepath"])
        data["metadata"] = data.get("metadata", {})

        return cls(**data)

    @staticmethod
    def validate_json(data: Dict[str, Any]) -> None:
        if SAMPLE_TO_NES_NAME not in data.get("metadata", {}):
            raise InvalidReconstructionError("Metadata is missing. Probably not a valid reconstruction file.")

        for field in [
            "approximation",
            "approximations",
            "instructions",
            "config",
            "coefficient",
            "audio_filepath",
            "metadata",
        ]:
            if field not in data:
                raise InvalidReconstructionError(f"Reconstruction data is missing '{field}' field.")

    def export(self, as_string: bool = False) -> Dict[GeneratorName, Dict[FeatureKey, Union[str, FeatureValue]]]:
        features = {}
        for name, instructions in self.instructions.items():
            if not instructions:
                continue

            exporter_class = self._get_exporter_class(instructions[0])
            exporter = exporter_class()
            features[name] = exporter(instructions, as_string=as_string)

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
