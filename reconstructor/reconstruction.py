import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Self, Union

import numpy as np
from pydantic import BaseModel, Field, field_serializer

from config import Config
from exporters.exporter import FeatureKey, FeatureValue
from exporters.noise import NoiseExporter
from exporters.square import SquareExporter
from exporters.triangle import TriangleExporter
from instructions.instruction import Instruction
from instructions.noise import NoiseInstruction
from instructions.square import SquareInstruction
from instructions.triangle import TriangleInstruction
from reconstructor.state import ReconstructionState
from utils import deserialize_array, serialize_array

INSTRUCTION_CLASS_MAP = {
    "Instruction": Instruction,
    "TriangleInstruction": TriangleInstruction,
    "SquareInstruction": SquareInstruction,
    "NoiseInstruction": NoiseInstruction,
}

INSTRUCTION_TO_EXPORTER_MAP = {
    TriangleInstruction: TriangleExporter,
    SquareInstruction: SquareExporter,
    NoiseInstruction: NoiseExporter,
}


class Reconstruction(BaseModel):
    approximation: np.ndarray = Field(..., description="Audio approximation")
    approximations: Dict[str, np.ndarray] = Field(..., description="Approximations per generator")
    instructions: Dict[str, List[Instruction]] = Field(..., description="Instructions per generator")
    errors: Dict[str, List[float]] = Field(..., description="Reconstruction errors per generator")
    config: Config = Field(..., description="Configuration used for reconstruction")

    @staticmethod
    def _get_instruction_class(
        name: Literal["Instruction", "TriangleInstruction", "SquareInstruction", "NoiseInstruction"] = None,
    ) -> Dict[str, type]:
        return INSTRUCTION_CLASS_MAP[name]

    @staticmethod
    def _get_exporter_class(instruction: Instruction) -> Dict[type, type]:
        return INSTRUCTION_TO_EXPORTER_MAP[type(instruction)]

    @classmethod
    def _parse_instructions(cls, data: Dict[str, Dict[str, Any]]) -> Dict[str, List[Instruction]]:
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
    def from_results(cls, state: ReconstructionState, config: Config) -> Self:
        approximations = {name: np.concatenate(state.approximations[name]) for name in state.approximations}
        approximation = np.sum(np.array(list(approximations.values())), axis=0)

        return cls(
            approximation=approximation,
            approximations=approximations,
            instructions=state.instructions,
            errors=state.errors,
            config=config,
        )

    def get_generator_approximation(self, generator_name: str) -> np.ndarray:
        return self.approximations.get(generator_name, np.array([]))

    def get_generator_instructions(self, generator_name: str) -> List[Instruction]:
        return self.instructions.get(generator_name, [])

    def save(self, filepath: Path) -> None:
        data = self.model_dump()
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> Self:
        with open(filepath, "r") as f:
            data = json.load(f)

        data["approximation"] = deserialize_array(data["approximation"])
        data["approximations"] = {name: deserialize_array(array) for name, array in data["approximations"].items()}
        data["instructions"] = cls._parse_instructions(data["instructions"])
        data["config"] = Config(**data["config"])

        return cls(**data)

    def export(self, as_string: bool = True) -> Dict[str, Dict[FeatureKey, Union[str, FeatureValue]]]:
        features = {}
        for name, instructions in self.instructions.items():
            if not instructions:
                continue

            exporter_class = self._get_exporter_class(instructions[0])
            exporter = exporter_class()
            features[name] = exporter(instructions, as_string=as_string)

        return features

    @field_serializer("approximation")
    def _serialize_approximation(self, approximation: np.ndarray, _info) -> Dict[str, Any]:
        return serialize_array(approximation)

    @field_serializer("approximations")
    def _serialize_approximations(self, approximations: Dict[str, np.ndarray], _info) -> Dict[str, Any]:
        return {name: serialize_array(array) for name, array in approximations.items()}

    @field_serializer("instructions")
    def _serialize_instructions(self, instructions: Dict[str, List[Instruction]], _info) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "instructions": [instruction.model_dump() for instruction in instructions],
                "type": type(instructions[0]).__name__,
            }
            for name, instructions in instructions.items()
            if instructions
        }

    @field_serializer("config")
    def _serialize_config(self, config: Config, _info) -> Dict[str, Any]:
        return config.model_dump()

    class Config:
        arbitrary_types_allowed = True
