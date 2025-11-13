import json
from functools import cached_property
from pathlib import Path
from typing import Collection, Dict, Generic, List, Self, Type, Union

import msgpack
import numpy as np
from pydantic import BaseModel, ConfigDict, field_serializer

from sampletones.configs import Config, LibraryConfig
from sampletones.constants.enums import GeneratorClassName
from sampletones.constants.general import LIBRARY_PHASES_PER_SAMPLE
from sampletones.ffts import CyclicArray, Window
from sampletones.ffts.transformations import FFTTransformer
from sampletones.generators import GENERATOR_CLASS_MAP, GeneratorType
from sampletones.instructions import InstructionType, InstructionUnion
from sampletones.typehints import Initials, SerializedData
from sampletones.utils import deserialize_array, dump, serialize_array

from .fragment import Fragment


class LibraryFragment(BaseModel, Generic[InstructionType, GeneratorType]):
    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)

    generator_class: GeneratorClassName
    instruction: InstructionType
    sample: CyclicArray
    feature: np.ndarray
    frequency: float

    @classmethod
    def create(
        cls,
        generator: GeneratorType,
        instruction: InstructionType,
        window: Window,
        transformer: FFTTransformer,
    ) -> Self:
        sample: CyclicArray = generator.generate_sample(instruction)

        features = []
        for phase_id in range(LIBRARY_PHASES_PER_SAMPLE):
            phase = phase_id / LIBRARY_PHASES_PER_SAMPLE
            windowed_audio = sample.get_window(phase, window)
            transformed_windowed_audio = transformer.calculate(windowed_audio)
            features.append(transformed_windowed_audio)

        feature = transformer.inverse(np.mean(features, axis=0))

        return cls(
            generator_class=generator.class_name(),
            instruction=instruction,
            sample=sample,
            feature=feature,
            frequency=generator.timer.real_frequency,
        )

    def get_fragment(self, shift: int, config: Config, window: Window) -> Fragment:
        windowed_audio = self.sample.get_window(shift, window)
        audio = window.get_frame_from_window(windowed_audio)
        return Fragment(
            audio=audio,
            feature=self.feature,
            windowed_audio=windowed_audio,
            config=config,
        )

    def get(
        self,
        generator: GeneratorType,
        config: Config,
        window: Window,
        initials: Initials = None,
    ) -> Fragment:
        generator.set_timer(self.instruction)
        shift = generator.timer.calculate_offset(initials)
        return self.get_fragment(shift, config, window)

    @property
    def data(self) -> np.ndarray:
        return self.sample.array

    @property
    def empty(self) -> bool:
        return len(self.sample.array) == 0

    @property
    def sample_length(self) -> int:
        return len(self.sample.array)

    @staticmethod
    def load_instruction(data: SerializedData) -> InstructionType:
        instruction_dictionary = json.loads(data["instruction"])
        instruction_class: Type[InstructionType] = GENERATOR_CLASS_MAP[data["generator_class"]].get_instruction_type()
        instruction = instruction_class(**instruction_dictionary)
        return instruction

    @field_serializer("instruction")
    def serialize_instruction(self, instruction: InstructionType, _info) -> str:
        return dump(instruction.model_dump())

    @field_serializer("feature")
    def serialize_feature(self, feature: np.ndarray, _info) -> SerializedData:
        return serialize_array(feature)

    @classmethod
    def deserialize(cls, dictionary: SerializedData) -> Self:
        instruction: InstructionType = cls.load_instruction(dictionary)

        sample = CyclicArray.deserialize(dictionary["sample"])
        feature = deserialize_array(dictionary["feature"])
        return cls(
            generator_class=dictionary["generator_class"],
            instruction=instruction,
            sample=sample,
            feature=feature,
            frequency=dictionary["frequency"],
        )


class LibraryData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: LibraryConfig
    data: Dict[InstructionUnion, LibraryFragment]

    @cached_property
    def subdata(self) -> Dict[GeneratorClassName, Dict[InstructionUnion, LibraryFragment]]:
        subdata = {}
        for generator_class_name in GeneratorClassName:
            subdata[generator_class_name] = {
                instruction: fragment
                for instruction, fragment in self.data.items()
                if fragment.generator_class == generator_class_name
            }

        return subdata

    def __getitem__(self, key: InstructionUnion) -> LibraryFragment:
        return self.data[key]

    def filter(
        self, generator_classes: Union[GeneratorClassName, Collection[GeneratorClassName]]
    ) -> Dict[InstructionUnion, LibraryFragment]:
        if not generator_classes:
            return {}

        if isinstance(generator_classes, GeneratorClassName):
            return self.subdata.get(generator_classes, {})
        elif isinstance(generator_classes, Collection):
            result: Dict[InstructionUnion, LibraryFragment] = {}
            for generator_class_name in generator_classes:
                result |= self.subdata[generator_class_name]
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
        assert binary is not None, "Failed to serialize LibraryData"
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
    def serialize_data(self, data: Dict[InstructionUnion, LibraryFragment], _info) -> SerializedData:
        return {dump(instruction.model_dump()): fragment.model_dump() for instruction, fragment in data.items()}

    @classmethod
    def deserialize(cls, dictionary: SerializedData) -> Self:
        config = LibraryConfig(**dictionary["config"])

        data = {}
        for key, value in dictionary["data"].items():
            instruction: InstructionUnion = LibraryFragment.load_instruction(
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
