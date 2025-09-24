import base64
import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from pydantic import BaseModel, Field

from instructions.instruction import Instruction
from instructions.noise import NoiseInstruction
from instructions.square import SquareInstruction
from instructions.triangle import TriangleInstruction


class Reconstruction(BaseModel):
    audio_data: bytes = Field(..., description="Base64 encoded numpy array")
    audio_shape: tuple = Field(..., description="Original shape of the audio array")
    audio_dtype: str = Field(..., description="Original dtype of the audio array")
    instructions: Dict[str, List[Instruction]] = Field(..., description="Instructions per generator")
    total_error: float = Field(..., description="Total reconstruction error")

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

    def __repr__(self) -> str:
        return (
            f"Reconstruction(audio_shape={self.audio_shape}, "
            f"audio_dtype={self.audio_dtype}, "
            f"total_error={self.total_error}, "
            f"generators={list(self.instructions.keys())})"
        )

    @classmethod
    def from_results(
        cls, audio: np.ndarray, instructions: Dict[str, List[Instruction]], total_error: float
    ) -> "Reconstruction":
        audio_bytes = base64.b64encode(audio.tobytes()).decode("utf-8")

        return cls(
            audio_data=audio_bytes.encode("utf-8"),
            audio_shape=audio.shape,
            audio_dtype=str(audio.dtype),
            instructions=instructions,
            total_error=total_error,
        )

    @property
    def audio(self) -> np.ndarray:
        audio_bytes = base64.b64decode(self.audio_data.decode("utf-8"))
        return np.frombuffer(audio_bytes, dtype=np.dtype(self.audio_dtype)).reshape(self.audio_shape)

    def save_json(self, filepath: Path) -> None:
        data = self.model_dump()
        data["audio_data"] = self.audio_data.decode("utf-8")
        data["instructions"] = self._serialize_instructions(data["instructions"])

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_json(cls, filepath: Path) -> "Reconstruction":
        with open(filepath, "r") as f:
            data = json.load(f)

        data["audio_data"] = data["audio_data"].encode("utf-8")
        data["instructions"] = cls._deserialize_instructions(data["instructions"])

        return cls(**data)

    def save_npz(self, filepath: Path) -> None:
        np.savez_compressed(filepath.with_suffix(".npz"), audio=self.audio)

        metadata = {"instructions": self._serialize_instructions(self.instructions), "total_error": self.total_error}

        with open(filepath.with_suffix(".json"), "w") as f:
            json.dump(metadata, f, indent=2)

    @classmethod
    def load_npz(cls, filepath: Path) -> "Reconstruction":
        audio_data = np.load(filepath.with_suffix(".npz"))["audio"]

        with open(filepath.with_suffix(".json"), "r") as f:
            metadata = json.load(f)

        reconstructed_instructions = cls._deserialize_instructions(metadata["instructions"])

        return cls.from_results(
            audio=audio_data, instructions=reconstructed_instructions, total_error=metadata["total_error"]
        )
