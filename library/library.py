import hashlib
import json
from functools import cached_property
from pathlib import Path
from typing import Any, Collection, Dict, Self, Union, cast

import msgpack
import numpy as np
from pydantic import BaseModel, Field, field_serializer
from tqdm.auto import tqdm

from config import Config as Config
from constants import LIBRARY_PATH, MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from ffts.fft import calculate_fft
from ffts.window import Window
from generators.generator import Generator
from generators.noise import NoiseGenerator
from generators.pulse import PulseGenerator
from generators.triangle import TriangleGenerator
from instructions.instruction import Instruction
from library.fragment import Fragment
from typehints.general import GeneratorClassName, GeneratorClassNameValues, Initials
from typehints.generators import GeneratorClass, GeneratorUnion
from typehints.instructions import InstructionUnion
from utils import deserialize_array, dump, serialize_array

GENERATORS: Dict[GeneratorClassName, GeneratorClass] = {
    "PulseGenerator": PulseGenerator,
    "TriangleGenerator": TriangleGenerator,
    "NoiseGenerator": NoiseGenerator,
}


def load_instruction(data: Dict[str, Any]) -> InstructionUnion:
    instruction_dictionary = json.loads(data["instruction"])
    instruction_class = GENERATORS[data["generator_class"]].get_instruction_type()
    instruction = instruction_class(**instruction_dictionary)
    return instruction


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
    instruction: InstructionUnion
    sample: np.ndarray
    feature: np.ndarray
    frequency: float
    offset: int

    @classmethod
    def create(cls, generator: GeneratorUnion, instruction: InstructionUnion, window: Window) -> Self:
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
            frequency=generator.timer.real_frequency,
            offset=offset,
        )

    def get_fragment(self, shift: int, window: Window) -> Fragment:
        offset = self.offset + shift
        windowed_audio = window.get_windowed_frame(self.sample, offset)
        audio = window.get_frame_from_window(windowed_audio)
        return Fragment(audio=audio, feature=self.feature, windowed_audio=windowed_audio)

    def get(self, generator: Generator, window: Window, initials: Initials = None) -> Fragment:
        generator.set_timer(self.instruction)
        shift = generator.timer.calculate_offset(initials)
        return self.get_fragment(shift, window)

    @field_serializer("instruction")
    def serialize_instruction(self, instruction: Instruction, _info) -> str:
        return dump(instruction.model_dump())

    @field_serializer("sample")
    def serialize_sample(self, sample: np.ndarray, _info) -> Dict[str, Any]:
        return serialize_array(sample)

    @field_serializer("feature")
    def serialize_feature(self, feature: np.ndarray, _info) -> Dict[str, Any]:
        return serialize_array(feature)

    @classmethod
    def deserialize(cls, dictionary: Dict[str, Any]) -> Self:
        instruction: InstructionUnion = load_instruction(dictionary)

        sample = deserialize_array(dictionary["sample"])
        feature = deserialize_array(dictionary["feature"])
        return cls(
            generator_class=dictionary["generator_class"],
            instruction=instruction,
            sample=sample,
            feature=feature,
            frequency=dictionary["frequency"],
            offset=dictionary["offset"],
        )

    class Config:
        arbitrary_types_allowed = True


class LibraryData(BaseModel):
    data: Dict[InstructionUnion, LibraryFragment]

    @cached_property
    def subdata(self) -> Dict[GeneratorClassName, Dict[InstructionUnion, LibraryFragment]]:
        subdata = {}
        for generator_class_name in GeneratorClassNameValues:
            generator_class_literal = cast(GeneratorClassName, generator_class_name)
            subdata[generator_class_literal] = {
                instruction: fragment
                for instruction, fragment in self.data.items()
                if fragment.generator_class == generator_class_literal
            }

        return subdata

    def __getitem__(self, key: InstructionUnion) -> LibraryFragment:
        return self.data[key]

    def filter(
        self, generator_classes: Union[GeneratorClassName, Collection[GeneratorClassName]]
    ) -> Dict[InstructionUnion, LibraryFragment]:
        if not generator_classes:
            return {}

        if isinstance(generator_classes, str):
            return self.subdata.get(generator_classes, {})
        elif isinstance(generator_classes, Collection):
            result: Dict[InstructionUnion, LibraryFragment] = {}
            for generator_class in generator_classes:
                generator_class_literal = cast(GeneratorClassName, generator_class)
                result |= self.subdata[generator_class_literal]
            return result

        raise ValueError("Incorrect type of generator class provided")

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()

    @field_serializer("data")
    def serialize_data(self, data: Dict[InstructionUnion, LibraryFragment], _info) -> Dict[str, Any]:
        return {dump(k.model_dump()): v.model_dump() for k, v in data.items()}

    @classmethod
    def deserialize(cls, dictionary: Dict[str, Any]) -> Self:
        data = {}
        for key, value in dictionary["data"].items():

            instruction: InstructionUnion = load_instruction(
                {
                    "instruction": key,
                    "generator_class": value["generator_class"],
                }
            )

            fragment: LibraryFragment = LibraryFragment.deserialize(value)
            data[instruction] = fragment

        return cls(data=data)

    class Config:
        arbitrary_types_allowed = True


class Library(BaseModel):
    path: str = Field(LIBRARY_PATH, description="Path to the FFT library file")
    data: Dict[LibraryKey, LibraryData] = Field(..., default_factory=dict, description="FFT library data")

    def __getitem__(self, key: LibraryKey) -> LibraryData:
        return self.data[key]

    def get(self, config: Config, window: Window) -> LibraryData:
        key = LibraryKey.create(config, window)
        if key not in self.data:
            self.update(config, window)

        return self.data[key]

    def update(self, config: Config, window: Window, overwrite: bool = False) -> LibraryKey:
        key = LibraryKey.create(config, window)
        if not overwrite and key in self.data:
            return key

        generators = {name: GENERATORS[name](config, name) for name in GENERATORS}
        data = {}
        for generator in tqdm(generators.values(), desc="Generating FFT library"):
            for instruction in tqdm(
                generator.get_possible_instructions(), desc=f"Processing {generator.name}", leave=False
            ):
                fragment = LibraryFragment.create(generator, instruction, window)
                data[instruction] = fragment

        self.data[key] = LibraryData(data=data)
        self._save()
        return key

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()

    def _save(self):
        dump = self.model_dump()
        binary = msgpack.packb(dump)
        path = Path(self.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as file:
            file.write(binary)

    def _load(self):
        with open(self.path, "rb") as file:
            binary = file.read()

        dump = msgpack.unpackb(binary)
        self.path = Path(dump["path"])
        self.data = {LibraryKey.deserialize(key): LibraryData.deserialize(data) for key, data in dump["data"].items()}

    @field_serializer("data")
    def serialize_data(self, data: Dict[LibraryKey, LibraryData], _info) -> Dict[str, Any]:
        return {dump(k.model_dump()): v.model_dump() for k, v in data.items()}

    @classmethod
    def load(cls, path: str = LIBRARY_PATH) -> Self:
        library = cls(path=path)
        if Path(path).exists():
            library._load()

        return library

    class Config:
        arbitrary_types_allowed = True
