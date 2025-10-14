import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Self

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
from generators.types import GeneratorClassName, Initials
from instructions.instruction import Instruction
from library.fragment import Fragment
from timers.timer import Timer
from utils import dump

GENERATORS = {
    "SquareGenerator": SquareGenerator,
    "TriangleGenerator": TriangleGenerator,
    "NoiseGenerator": NoiseGenerator,
}


class LibraryKey(BaseModel):
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


class LibraryFragment(BaseModel):
    generator_class: GeneratorClassName
    instruction: Instruction
    sample: np.ndarray
    feature: np.ndarray
    frequency: float
    offset: int

    @classmethod
    def create(cls, generator: Generator, instruction: Instruction, window: Window) -> Self:
        sample, offset = generator.generate_sample(instruction, window=window)
        audio = generator.generate_frames(instruction)
        frames_count = audio.shape[0] // generator.frame_length
        start_id = int(np.ceil(0.5 * window.size / generator.frame_length))
        end_id = frames_count - start_id
        feature = np.log1p(
            np.mean(
                [
                    np.abs(calculate_fft(window.get_windowed_frame(audio, frame_id * generator.frame_length)))
                    for frame_id in range(start_id, end_id)
                ],
                axis=0,
            )
        )
        return cls(
            generator_class=generator.class_name(),
            instruction=instruction,
            sample=sample,
            feature=feature,
            frequency=generator.get_frequency(instruction.pitch) if instruction.on else 0,
            offset=offset,
        )

    def get(self, generator: Generator, window: Window, initials: Initials = None) -> Fragment:
        generator.set_timer(self.instruction)
        offset = generator.timer.calculate_offset(initials) + self.offset
        windowed_audio = window.get_windowed_frame(self.sample, offset)
        audio = window.get_frame_from_window(windowed_audio)
        return Fragment(audio=audio, feature=self.feature, windowed_audio=windowed_audio)

    class Config:
        arbitrary_types_allowed = True


class LibraryData(BaseModel):
    data: Dict[Instruction, LibraryFragment]

    def __getitem__(self, key: Instruction) -> LibraryFragment:
        return self.data[key]

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()

    class Config:
        arbitrary_types_allowed = True


class Library(BaseModel):
    path: str = Field(LIBRARY_PATH, description="Path to the FFT library file")
    data: Dict[LibraryKey, LibraryData] = Field(..., default_factory=dict, description="FFT library data")

    def __getitem__(self, key: LibraryKey) -> LibraryData:
        return self.data[key]

    def update(self, config: Config, window: Window, duration: float = 3.0, overwrite: bool = False) -> LibraryKey:
        key = LibraryKey.create(config, window)
        if not overwrite and key in self.data:
            return key

        generators = {name: GENERATORS[name](config, name) for name in GENERATORS}
        log_arffts = {}
        for generator in tqdm(generators.values(), desc="Generating FFT library"):
            if generator.name in log_arffts:
                continue

            generator_data = self._calculate_generator_data(key, generator, window, duration)
            log_arffts[generator.name] = generator_data

        self.data[key] = LibraryData(data=log_arffts)
        self.save()
        return key

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
        self.data = {}

    @field_serializer("path")
    def serialize_path(self, path: Path, _info):
        return str(path)

    @field_serializer("data")
    def serialize_data(self, data: Dict[LibraryKey, LibraryData], _info) -> Dict[str, Any]:
        return {dump(k.model_dump()): v.model_dump() for k, v in data.items()}

    @classmethod
    def load(cls, path: Path) -> Self:
        library = cls(path=path)
        library._load()
        return library

    class Config:
        arbitrary_types_allowed = True
