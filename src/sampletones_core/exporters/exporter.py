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
    """
    Converts between a channel's instruction sequence and FamiTracker features.

    An instruction sequence describes a channel frame by frame; a :class:`Features`
    value describes the same channel as the per-dimension envelopes (volume, arpeggio,
    pitch, and timbre) a FamiTracker instrument uses. Each concrete exporter binds one
    instruction type to its feature layout through ``_ATTRIBUTE_MAP`` and defines how a
    row of feature values becomes an instruction.

    `to_features` runs the instructions-to-features direction, and `from_features` runs
    the reverse.
    """

    _ATTRIBUTE_MAP: Dict[FeatureKey, InstructionFields]

    def to_features(
        self,
        instructions: List[InstructionT],
    ) -> Features:
        """Converts an instruction sequence into its :class:`Features`.

        Args:
            instructions: The channel's per-frame instructions.

        Returns:
            Features: The envelope representation of the sequence.
        """
        feature_map = self.get_feature_map(instructions)
        return self.from_feature_map_to_features(feature_map)

    @staticmethod
    def from_feature_map_to_features(feature_map: FeatureMap) -> Features:
        """Builds trimmed :class:`Features` from a raw feature map.

        Trims each envelope to the span ending just after the last audible frame, so
        trailing silence is dropped from every dimension together.

        Args:
            feature_map: The raw per-dimension arrays.

        Returns:
            Features: The trimmed features.
        """
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
    def get_feature_map(cls, instructions: List[InstructionT]) -> FeatureMap:
        """Extracts the raw per-dimension feature arrays from an instruction sequence.

        Args:
            instructions: The channel's per-frame instructions.

        Returns:
            FeatureMap: The per-dimension arrays for this channel.
        """

    @classmethod
    def from_features(cls, features: Features) -> List[InstructionT]:
        """Rebuilds the instruction sequence from a :class:`Features`.

        Walks the envelopes frame by frame, reading each dimension's value (holding the
        previous instruction's value past the end of a shorter envelope) and assembling
        one instruction per frame.

        Args:
            features: The envelope representation of a channel.

        Returns:
            List[InstructionT]: The reconstructed per-frame instructions.
        """
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
    ) -> InstructionT:
        """Builds one instruction from a row of feature values.

        Args:
            dictionary: The per-attribute values for one frame.
            initial_pitch: The sequence's reference pitch, added back to a relative pitch.

        Returns:
            InstructionT: The instruction for that frame.
        """

    @staticmethod
    def _infer_instruction_on(dictionary: Dict[str, Union[bool, int]]) -> bool:
        if "on" in dictionary:
            return bool(dictionary["on"])

        if "volume" in dictionary:
            return dictionary["volume"] > 0

        return True

    @classmethod
    def _handle_special_attributes(
        cls,
        attribute: InstructionFields,
        value: int,
        initial_value: int,
    ) -> int:
        if attribute == "pitch":
            value -= initial_value

        return value

    @classmethod
    def get_value(
        cls,
        attribute: InstructionFields,
        array: Optional[np.ndarray],
        last_instruction: Optional[InstructionT],
        index: int,
        initial_value: int = 0,
    ) -> int:
        """Reads one attribute's value for a given frame.

        Returns the array's value at ``index`` when present; past the array's end it
        carries the previous instruction's value forward, and falls back to
        ``initial_value`` when neither is available.

        Args:
            attribute: The instruction field being read.
            array: The dimension's envelope, or ``None``.
            last_instruction: The instruction from the previous frame, if any.
            index: The frame position to read.
            initial_value: The value used when the array is empty or exhausted.

        Returns:
            int: The attribute's value for the frame.
        """
        if array is None or not array.size:
            return initial_value

        if index < len(array):
            return int(array[index])

        if last_instruction is not None:
            if hasattr(last_instruction, attribute):
                value = int(getattr(last_instruction, attribute))
                return cls._handle_special_attributes(attribute, value, initial_value)

        return initial_value

    @classmethod
    def _remap_feature_key(cls, feature_key: FeatureKey) -> Optional[InstructionFields]:
        if not hasattr(cls, "_ATTRIBUTE_MAP"):
            raise NotImplementedError("Subclasses must define _ATTRIBUTE_MAP")

        return cls._ATTRIBUTE_MAP.get(feature_key)

    @staticmethod
    def pitch_to_timer(pitch: int) -> int:
        """Converts a MIDI pitch to its NES timer period.

        Args:
            pitch: The MIDI pitch.

        Returns:
            int: The timer period that sounds the pitch.
        """
        frequency = pitch_to_frequency(pitch)
        return PhaseTimer.frequency_to_timer(frequency)

    @classmethod
    @abstractmethod
    def get_instruction_type(cls) -> InstructionTypeUnion:
        """The instruction type this exporter handles.

        Returns:
            InstructionTypeUnion: The concrete instruction type.
        """

    @classmethod
    @abstractmethod
    def get_generator_type(cls) -> GeneratorTypeUnion:
        """The generator type paired with this exporter.

        Returns:
            GeneratorTypeUnion: The concrete generator type.
        """
