import hashlib
import json
from pathlib import Path
from typing import Dict, Literal, Tuple

import h5py
import numpy as np
from flask import json
from pydantic import BaseModel, Field
from tqdm.auto import tqdm

from config import Config as Config
from constants import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from ffts.fft import calculate_fft
from ffts.window import Window
from generators.generator import Generator
from generators.noise import NoiseGenerator
from generators.square import SquareGenerator
from generators.triangle import TriangleGenerator
from instructions.instruction import Instruction

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
    def create(cls, config: Config, window: Window) -> "FFTLibraryKey":
        config_fields = {
            "change_rate": config.change_rate,
            "sample_rate": config.sample_rate,
            "a4_frequency": config.a4_frequency,
            "a4_pitch": config.a4_pitch,
            "min_pitch": config.min_pitch,
            "max_pitch": config.max_pitch,
        }
        json_string = json.dumps(config_fields, separators=(",", ":"))
        config_hash = hashlib.sha256(json_string.encode("utf-8")).hexdigest()
        return cls(
            sample_rate=config.sample_rate,
            frame_length=window.frame_length,
            window_size=window.size,
            config_hash=config_hash,
        )

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

    class Config:
        arbitrary_types_allowed = True


class FFTLibrary(BaseModel):
    path: Path = Field(..., description="Path to the FFT library file")
    data: Dict[FFTLibraryKey, FFTLibraryData] = Field(..., default_factory=dict, description="FFT library data")

    def __post_init__(self):
        pass

    def __getitem__(self, key: FFTLibraryKey) -> FFTLibraryData:
        return self.data[key]

    def update(self, config: Config, window: Window, duration: float = 3.0, overwrite: bool = False) -> FFTLibraryKey:
        key = FFTLibraryKey.create(config, window)
        if not overwrite and key in self.data:
            return key

        generators = {name: GENERATORS[name](name, config) for name in GENERATORS}
        log_arffts = {}
        for generator in tqdm(generators.values(), desc="Generating FFT library"):
            if generator.name in log_arffts:
                continue

            generator_data = self.calculate_generator_data(key, generator, window, duration)
            log_arffts[generator.name] = generator_data

        self.data[key] = FFTLibraryData(data=log_arffts)
        self.save()
        return key

    def calculate_generator_data(
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

    def flatten(self, key: FFTLibraryKey) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
        instructions = {generator_type: list(values.keys()) for generator_type, values in self[key].items()}
        data = {generator_type: np.array(list(values.values())) for generator_type, values in self[key].items()}
        return instructions, data

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with h5py.File(self.path, "w") as f:
            for key, library_data in self.data.items():
                group_name = f"{key.sample_rate}_{key.frame_length}_{key.window_size}_{key.config_hash}"
                group = f.create_group(group_name)
                for generator_type, generator_data in library_data.items():
                    gen_group = group.create_group(generator_type)
                    instructions = np.array([str(instr) for instr in generator_data.keys()], dtype="S")
                    arffts = np.array(list(generator_data.values()))
                    gen_group.create_dataset("instructions", data=instructions)
                    gen_group.create_dataset("log_arffts", data=arffts)

    def load(self):
        pass

    class Config:
        arbitrary_types_allowed = True
