import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Literal, Self, Tuple

import msgpack
import numpy as np
from flask import json
from pydantic import BaseModel, Field, field_serializer
from tqdm.auto import tqdm

from config import Config as Config
from constants import LIBRARY_PATH, MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from ffts.fft import calculate_fft
from ffts.window import Window
from generators.generator import Generator
from generators.noise import NoiseGenerator
from generators.square import SquareGenerator
from generators.triangle import TriangleGenerator
from instructions.instruction import Instruction
from utils import deserialize_array, dump, serialize_array

GENERATORS = {
    "SquareGenerator": SquareGenerator,
    "TriangleGenerator": TriangleGenerator,
    "NoiseGenerator": NoiseGenerator,
}

GeneratorType = Literal["SquareGenerator", "TriangleGenerator", "NoiseGenerator"]


class FFTLibraryKey(BaseModel):
    sample_rate: int = Field(..., ge=MIN_SAMPLE_RATE, le=MAX_SAMPLE_RATE, description="Sample rate of the audio")
    frame_length: int = Field(..., ge=1, description="Length of a single frame")
    window_size: int = Field(..., ge=1, description="Size of the FFT window")
    config_hash: str = Field(..., description="Hash of the configuration")

    @classmethod
    def create(cls, config: Config, window: Window) -> Self:
        config_fields = {
            "change_rate": config.change_rate,
            "sample_rate": config.sample_rate,
            "a4_frequency": config.a4_frequency,
            "a4_pitch": config.a4_pitch,
        }
        json_string = dump(config_fields)
        config_hash = hashlib.sha256(json_string.encode("utf-8")).hexdigest()
        return cls(
            sample_rate=config.sample_rate,
            frame_length=window.frame_length,
            window_size=window.size,
            config_hash=config_hash,
        )

    @classmethod
    def deserialize(cls, string: str) -> Self:
        dictionary = json.loads(string)
        return cls(**dictionary)

    class Config:
        frozen = True


class FFTLibraryGeneratorData(BaseModel):
    generator_name: GeneratorType
    log_arffts: Dict[Instruction, np.ndarray]

    def __getitem__(self, key: Instruction) -> np.ndarray:
        return self.log_arffts[key]

    def keys(self):
        return self.log_arffts.keys()

    def items(self):
        return self.log_arffts.items()

    def values(self):
        return self.log_arffts.values()

    @field_serializer("log_arffts")
    def serialize_arrays(self, log_arffts: Dict[Instruction, np.ndarray], _info) -> Dict[str, Dict[str, Any]]:
        encoded = {}
        for instruction, array in log_arffts.items():
            key = dump(instruction.model_dump())
            encoded[key] = serialize_array(array)

        return encoded

    @classmethod
    def deserialize(cls, dictionary: Dict[str, Any]) -> Self:
        generator_name = dictionary["generator_name"]
        raw_log_arffts = dictionary["log_arffts"]
        log_arffts = {}
        for instruction_string, array_dictionary in raw_log_arffts.items():
            instruction_dictionary = json.loads(instruction_string)
            instruction_class = GENERATORS[generator_name].get_instruction_type()
            instruction = instruction_class(**instruction_dictionary)
            array = deserialize_array(array_dictionary)
            log_arffts[instruction] = array

        return cls(generator_name=generator_name, log_arffts=log_arffts)

    class Config:
        arbitrary_types_allowed = True


class FFTLibraryData(BaseModel):
    data: Dict[GeneratorType, FFTLibraryGeneratorData]

    def __getitem__(self, key: GeneratorType) -> FFTLibraryGeneratorData:
        return self.data[key]

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()

    @classmethod
    def deserialize(cls, dictionary: Dict[str, Any]) -> Self:
        data = dictionary["data"]
        return cls(
            data={
                generator_type: FFTLibraryGeneratorData.deserialize(generator_data)
                for generator_type, generator_data in data.items()
            }
        )

    class Config:
        arbitrary_types_allowed = True


class FFTLibrary(BaseModel):
    path: str = Field(LIBRARY_PATH, description="Path to the FFT library file")
    data: Dict[FFTLibraryKey, FFTLibraryData] = Field(..., default_factory=dict, description="FFT library data")

    def __getitem__(self, key: FFTLibraryKey) -> FFTLibraryData:
        return self.data[key]

    def update(self, config: Config, window: Window, duration: float = 3.0, overwrite: bool = False) -> FFTLibraryKey:
        key = FFTLibraryKey.create(config, window)
        if not overwrite and key in self.data:
            return key

        generators = {name: GENERATORS[name](config, name) for name in GENERATORS}
        log_arffts = {}
        for generator in tqdm(generators.values(), desc="Generating FFT library"):
            if generator.name in log_arffts:
                continue

            generator_data = self._calculate_generator_data(key, generator, window, duration)
            log_arffts[generator.name] = generator_data

        self.data[key] = FFTLibraryData(data=log_arffts)
        self.save()
        return key

    def _calculate_generator_data(
        self, key: FFTLibraryKey, generator: Generator, window: Window, duration: float
    ) -> FFTLibraryGeneratorData:
        generator_data = {}
        for instruction in tqdm(generator.get_possible_instructions(), desc="Generating instructions' FFTs"):
            sample = generator(instruction, length=round(duration * key.sample_rate))
            frames_count = int(np.ceil(sample.shape[0] / key.frame_length))
            log_arfft = np.log1p(
                np.mean(
                    [
                        np.abs(calculate_fft(window.get_windowed_frame(sample, frame_id)))
                        for frame_id in range(frames_count)
                    ],
                    axis=0,
                )
            )

            generator_data[instruction] = log_arfft

        return FFTLibraryGeneratorData(generator_name=generator.name, log_arffts=generator_data)

    def _flatten(self, key: FFTLibraryKey) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
        instructions = {generator_type: list(values.keys()) for generator_type, values in self[key].items()}
        data = {generator_type: np.array(list(values.values())) for generator_type, values in self[key].items()}
        return instructions, data

    def _save(self):
        dump = self.model_dump()
        binary = msgpack.packb(dump)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "wb") as file:
            file.write(binary)

    def _load(self):
        with open(self.path, "rb") as file:
            binary = file.read()

        dump = msgpack.unpackb(binary)
        self.path = Path(dump["path"])
        self.data = {
            FFTLibraryKey.deserialize(key): FFTLibraryData.deserialize(data) for key, data in dump["data"].items()
        }

    @field_serializer("path")
    def serialize_path(self, path: Path, _info):
        return str(path)

    @field_serializer("data")
    def serialize_data(self, data: Dict[FFTLibraryKey, FFTLibraryData], _info) -> Dict[str, Any]:
        return {dump(k.model_dump()): v.model_dump() for k, v in data.items()}

    @classmethod
    def load(cls, path: Path) -> Self:
        library = cls(path=path)
        library._load()
        return library

    class Config:
        arbitrary_types_allowed = True
