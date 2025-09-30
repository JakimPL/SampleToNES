import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field

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


class Reconstruction(BaseModel):
    audio_data: bytes = Field(..., description="Base64 encoded numpy array")
    audio_shape: tuple = Field(..., description="Original shape of the audio array")
    audio_dtype: str = Field(..., description="Original dtype of the audio array")
    approximations: Dict[str, np.ndarray] = Field(..., description="Approximations per generator")
    instructions: Dict[str, List[Instruction]] = Field(..., description="Instructions per generator")
    total_error: float = Field(..., description="Total reconstruction error")
    config: Config = Field(..., description="Configuration used for reconstruction")

    class Config:
        arbitrary_types_allowed = True

    @staticmethod
    def _get_instruction_classes():
        return {
            "Instruction": Instruction,
            "TriangleInstruction": TriangleInstruction,
            "SquareInstruction": SquareInstruction,
            "NoiseInstruction": NoiseInstruction,
        }

    @staticmethod
    def _get_generator_exporter_classes(instruction: Instruction) -> Dict[type, type]:
        class_map = {
            TriangleInstruction: TriangleExporter,
            SquareInstruction: SquareExporter,
            NoiseInstruction: NoiseExporter,
        }

        return class_map[type(instruction)]

    @staticmethod
    def _serialize_instructions(instructions: Dict[str, List[Instruction]]) -> Dict[str, List[Any]]:
        serializable_instructions = {}
        for name, instruction_list in instructions.items():
            serializable_instructions[name] = []
            for instr in instruction_list:
                if hasattr(instr, "model_dump"):
                    instr_data = instr.model_dump()
                    instr_data["__class__"] = instr.__class__.__name__
                    serializable_instructions[name].append(instr_data)
                else:
                    serializable_instructions[name].append(str(instr))
        return serializable_instructions

    @classmethod
    def _deserialize_instructions(cls, instructions_data: Dict[str, List[Any]]) -> Dict[str, List[Instruction]]:
        instruction_classes = cls._get_instruction_classes()

        reconstructed_instructions = {}
        for name, instruction_list in instructions_data.items():
            reconstructed_instructions[name] = []
            for instr in instruction_list:
                if isinstance(instr, dict) and "__class__" in instr:
                    class_name = instr.pop("__class__")
                    instruction_class = instruction_classes.get(class_name, instruction_classes["Instruction"])
                    reconstructed_instructions[name].append(instruction_class(**instr))
                elif isinstance(instr, dict):
                    reconstructed_instructions[name].append(instruction_classes["Instruction"](**instr))
                else:
                    reconstructed_instructions[name].append(instr)
        return reconstructed_instructions

    @staticmethod
    def _serialize_approximations(approximations: Dict[str, np.ndarray]) -> Dict[str, Dict[str, Any]]:
        serializable_approximations = {}
        for name, array in approximations.items():
            serializable_approximations[name] = {
                "data": base64.b64encode(array.tobytes()).decode("utf-8"),
                "shape": array.shape,
                "dtype": str(array.dtype),
            }
        return serializable_approximations

    @staticmethod
    def _deserialize_approximations(approximations_data: Dict[str, Dict[str, Any]]) -> Dict[str, np.ndarray]:
        reconstructed_approximations = {}
        for name, array_data in approximations_data.items():
            array_bytes = base64.b64decode(array_data["data"].encode("utf-8"))
            array = np.frombuffer(array_bytes, dtype=np.dtype(array_data["dtype"]))
            reconstructed_approximations[name] = array.reshape(array_data["shape"])
        return reconstructed_approximations

    def __repr__(self) -> str:
        return (
            f"Reconstruction(audio_shape={self.audio_shape}, "
            f"audio_dtype={self.audio_dtype}, "
            f"total_error={self.total_error}, "
            f"generators={list(self.instructions.keys())}, "
            f"approximations={list(self.approximations.keys())})"
        )

    @classmethod
    def from_results(cls, state: ReconstructionState, config: Config) -> "Reconstruction":
        approximations = {name: np.concatenate(state.approximations[name]) for name in state.approximations}
        audio = np.sum(np.array(list(approximations.values())), axis=0)

        audio_bytes = base64.b64encode(audio.tobytes()).decode("utf-8")

        return cls(
            audio_data=audio_bytes.encode("utf-8"),
            audio_shape=audio.shape,
            audio_dtype=str(audio.dtype),
            approximations=approximations,
            instructions=state.instructions,
            total_error=state.total_error,
            config=config,
        )

    @property
    def audio(self) -> np.ndarray:
        audio_bytes = base64.b64decode(self.audio_data.decode("utf-8"))
        return np.frombuffer(audio_bytes, dtype=np.dtype(self.audio_dtype)).reshape(self.audio_shape)

    def get_generator_approximation(self, generator_name: str) -> np.ndarray:
        return self.approximations.get(generator_name, np.array([]))

    def get_generator_instructions(self, generator_name: str) -> List[Instruction]:
        return self.instructions.get(generator_name, [])

    def save_json(self, filepath: Path) -> None:
        data = self.model_dump()
        data["audio_data"] = self.audio_data.decode("utf-8")
        data["instructions"] = self._serialize_instructions(data["instructions"])
        data["approximations"] = self._serialize_approximations(data["approximations"])

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_json(cls, filepath: Path) -> "Reconstruction":
        with open(filepath, "r") as f:
            data = json.load(f)

        data["audio_data"] = data["audio_data"].encode("utf-8")
        data["instructions"] = cls._deserialize_instructions(data["instructions"])
        data["approximations"] = cls._deserialize_approximations(data["approximations"])

        return cls(**data)

    def save_npz(self, filepath: Path) -> None:
        save_dict = {"audio": self.audio}
        save_dict.update(self.approximations)
        np.savez_compressed(filepath.with_suffix(".npz"), **save_dict)

        metadata = {
            "instructions": self._serialize_instructions(self.instructions),
            "total_error": self.total_error,
            "audio_shape": self.audio_shape,
            "audio_dtype": self.audio_dtype,
            "approximation_keys": list(self.approximations.keys()),
        }

        with open(filepath.with_suffix(".json"), "w") as f:
            json.dump(metadata, f, indent=2)

    @classmethod
    def load_npz(cls, filepath: Path) -> "Reconstruction":
        npz_data = np.load(filepath.with_suffix(".npz"))
        audio_data = npz_data["audio"]

        with open(filepath.with_suffix(".json"), "r") as f:
            metadata = json.load(f)

        approximations = {}
        for key in metadata.get("approximation_keys", []):
            if key in npz_data:
                approximations[key] = npz_data[key]

        reconstructed_instructions = cls._deserialize_instructions(metadata["instructions"])
        audio_bytes = base64.b64encode(audio_data.tobytes()).decode("utf-8")

        return cls(
            audio_data=audio_bytes.encode("utf-8"),
            audio_shape=metadata["audio_shape"],
            audio_dtype=metadata["audio_dtype"],
            approximations=approximations,
            instructions=reconstructed_instructions,
            total_error=metadata["total_error"],
        )

    def export_instructions(self, as_string: bool = True) -> Dict[str, Dict[FeatureKey, Union[str, FeatureValue]]]:
        features = {}
        for name, instructions in self.instructions.items():
            if not instructions:
                continue

            exporter_class = self._get_generator_exporter_classes(instructions[0])
            exporter = exporter_class()
            features[name] = exporter(instructions, as_string=as_string)

        return features
