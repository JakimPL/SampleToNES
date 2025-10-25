import json
from functools import cached_property
from pathlib import Path
from typing import Any, Collection, Dict, List, Optional, Self, Union, cast

import msgpack
import numpy as np
from pydantic import BaseModel, field_serializer

from configs.config import Config as Configuration
from configs.library import LibraryConfig
from ffts.fft import FFTTransformer
from ffts.window import Window
from generators.generator import Generator
from instructions.instruction import Instruction
from library.fragment import Fragment
from reconstructor.maps import GENERATOR_CLASS_MAP
from typehints.general import GeneratorClassName, GeneratorClassNameValues, Initials
from typehints.generators import GeneratorUnion
from typehints.instructions import InstructionUnion
from utils.common import deserialize_array, dump, serialize_array


def load_instruction(data: Dict[str, Any]) -> InstructionUnion:
    instruction_dictionary = json.loads(data["instruction"])
    instruction_class = GENERATOR_CLASS_MAP[data["generator_class"]].get_instruction_type()
    instruction = instruction_class(**instruction_dictionary)
    return instruction


class LibraryFragment(BaseModel):
    generator_class: GeneratorClassName
    instruction: InstructionUnion
    sample: np.ndarray
    feature: np.ndarray
    frequency: float
    offset: int

    @classmethod
    def create(
        cls, generator: GeneratorUnion, instruction: InstructionUnion, window: Window, transformer: FFTTransformer
    ) -> Self:
        sample, offset = generator.generate_sample(instruction, window=window)
        audio = generator.generate_frames(instruction)
        frames_count = audio.shape[0] // generator.frame_length
        start_id = int(np.ceil(0.5 * window.size / generator.frame_length))
        end_id = frames_count - start_id

        features = []
        for frame_id in range(start_id, end_id):
            windowed_audio = window.get_windowed_frame(audio, frame_id * generator.frame_length)
            transformed_windowed_audio = transformer.calculate(windowed_audio)
            features.append(transformed_windowed_audio)

        feature = transformer.inverse(np.mean(features, axis=0))

        return cls(
            generator_class=generator.class_name(),
            instruction=instruction,
            sample=sample,
            feature=feature,
            frequency=generator.timer.real_frequency,
            offset=offset,
        )

    def get_fragment(self, shift: int, config: Configuration, window: Window) -> Fragment:
        offset = self.offset + shift
        windowed_audio = window.get_windowed_frame(self.sample, offset)
        audio = window.get_frame_from_window(windowed_audio)
        return Fragment(
            audio=audio,
            feature=self.feature,
            windowed_audio=windowed_audio,
            config=config,
        )

    def get(self, generator: Generator, config: Configuration, window: Window, initials: Initials = None) -> Fragment:
        generator.set_timer(self.instruction)
        shift = generator.timer.calculate_offset(initials)
        return self.get_fragment(shift, config, window)

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
    config: LibraryConfig
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

    def save(self, path: Union[str, Path]) -> None:
        dump = self.model_dump()
        binary = msgpack.packb(dump)
        path_object = Path(path)
        path_object.parent.mkdir(parents=True, exist_ok=True)
        with open(path_object, "wb") as file:
            file.write(binary)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "LibraryData":
        path_object = Path(path)
        with open(path_object, "rb") as file:
            binary = file.read()

        data = msgpack.unpackb(binary)
        return LibraryData.deserialize(data)

    @field_serializer("data")
    def serialize_data(self, data: Dict[InstructionUnion, LibraryFragment], _info) -> Dict[str, Any]:
        return {dump(instruction.model_dump()): fragment.model_dump() for instruction, fragment in data.items()}

    @classmethod
    def deserialize(cls, dictionary: Dict[str, Any]) -> Self:
        config = LibraryConfig(**dictionary["config"])

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

        return cls(config=config, data=data)

    @classmethod
    def merge(cls, library_data_list: List[Self]) -> Self:
        if not library_data_list:
            raise ValueError("Cannot merge an empty list of LibraryData")

        config: LibraryConfig = library_data_list[0].config
        merged_data: Dict[InstructionUnion, LibraryFragment] = {}
        for library_data in library_data_list:
            assert config == library_data.config
            merged_data.update(library_data.data)
            if config is None:
                config = library_data.config

        return cls(config=config, data=merged_data)

    class Config:
        arbitrary_types_allowed = True
