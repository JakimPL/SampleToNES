from abc import ABC, abstractmethod
from typing import Dict, Generic, Iterable, List, Optional, Union, cast

import numpy as np

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.generators import GeneratorTypeUnion
from sampletones_core.instructions import (
    InstructionFields,
    InstructionT,
    InstructionTypeUnion,
)
from sampletones_core.timers import PhaseTimer
from sampletones_core.types.feature import FeatureMap
from sampletones_core.utils.frequencies import pitch_to_frequency
from sampletones_shared.utils.arrays import trim

from .feature import Features


class Exporter(ABC, Generic[InstructionT]):
    _ATTRIBUTE_MAP: Dict[FeatureKey, InstructionFields]

    def to_features(
        self,
        instructions: List[InstructionT],
    ) -> Features:
        feature_map = self.get_feature_map(instructions)
        return self.from_feature_map_to_features(feature_map)

    @staticmethod
    def from_feature_map_to_features(feature_map: FeatureMap) -> Features:
        features = Features.from_feature_map(feature_map)
        last_nonzero_volume_index: Optional[int] = None
        try:
            last_nonzero_volume_index = features.volume.nonzero()[0][-1] + 2
        except IndexError:
            pass

        for key, value in features.items():
            if isinstance(value, np.ndarray):
                array = value[:last_nonzero_volume_index]
                trimmed_value = trim(array)
                features[key] = trimmed_value

        return features

    @classmethod
    @abstractmethod
    def get_feature_map(cls, instructions: List[InstructionT]) -> FeatureMap: ...

    @classmethod
    def from_features(cls, features: Features) -> List[InstructionT]:
        features_map = features.feature_map
        initial_pitch = features.initial_pitch
        instructions: List[InstructionT] = []
        last_instruction: Optional[InstructionT] = None
        non_empty_arrays: Iterable[np.ndarray] = cast(
            Iterable[np.ndarray],
            filter(lambda obj: isinstance(obj, np.ndarray), features_map.values()),
        )
        max_length = max(map(len, non_empty_arrays), default=0)
        for index in range(max_length):
            instruction_dictionary: Dict[str, Union[bool, int]] = {}
            for key, array in features_map.items():
                if key == FeatureKey.INITIAL_PITCH or array is None:
                    continue

                attribute = cls._remap_feature_key(key)
                if not attribute:
                    continue

                value = Exporter.get_value(
                    attribute,
                    cast(np.ndarray, array),
                    last_instruction,
                    index,
                    initial_value=initial_pitch if attribute == "pitch" else 0,
                )

                instruction_dictionary[attribute] = value

            instruction = cls._features_dictionary_to_instruction(instruction_dictionary, initial_pitch)
            instructions.append(instruction)
            last_instruction = instruction

        return instructions

    @classmethod
    @abstractmethod
    def _features_dictionary_to_instruction(
        cls,
        dictionary: Dict[str, Union[bool, int]],
        initial_pitch: int,
    ) -> InstructionT: ...

    @staticmethod
    def _infer_instruction_on(dictionary: Dict[str, Union[bool, int]]) -> bool:
        if "on" in dictionary:
            return bool(dictionary["on"])

        if "volume" in dictionary:
            return dictionary["volume"] > 0

        return True

    @classmethod
    def get_value(
        cls,
        attribute: InstructionFields,
        array: Optional[np.ndarray],
        last_instruction: Optional[InstructionT],
        index: int,
        initial_value: int = 0,
    ) -> int:
        if array is None or not array.size:
            return initial_value

        if index < len(array):
            return int(array[index])

        if last_instruction is not None:
            if hasattr(last_instruction, attribute):
                value = int(getattr(last_instruction, attribute))
                if attribute == "pitch":
                    value -= initial_value

                return value

            raise AttributeError(f"{last_instruction.__class__.__name__} does not have attribute '{attribute}'")

        return initial_value

    @classmethod
    def _remap_feature_key(cls, feature_key: FeatureKey) -> Optional[InstructionFields]:
        if not hasattr(cls, "_ATTRIBUTE_MAP"):
            raise NotImplementedError("Subclasses must define _ATTRIBUTE_MAP")

        return cls._ATTRIBUTE_MAP.get(feature_key)

    @staticmethod
    def pitch_to_timer(pitch: int) -> int:
        frequency = pitch_to_frequency(pitch)
        return PhaseTimer.frequency_to_timer(frequency)

    @classmethod
    @abstractmethod
    def get_instruction_type(cls) -> InstructionTypeUnion: ...

    @classmethod
    @abstractmethod
    def get_generator_type(cls) -> GeneratorTypeUnion: ...
