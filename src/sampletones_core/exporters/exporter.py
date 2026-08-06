from abc import ABC, abstractmethod
from typing import Dict, Final, Generic, List, Optional, Union, cast

import numpy as np

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.generators import GeneratorTypeUnion
from sampletones_core.instructions import (
    InstructionFields,
    InstructionT,
    InstructionTypeUnion,
)
from sampletones_core.types.feature import FeatureMap
from sampletones_shared.utils.arrays import hold, trim

from .feature import Features

EMPTY_ENVELOPE_VALUE: Final[int] = 0


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
        initial_pitch: int,
    ) -> Features:
        """Converts an instruction sequence into its :class:`Features`.

        Args:
            instructions: The channel's per-frame instructions.
            initial_pitch: Reference pitch the arpeggio envelope is measured against.

        Returns:
            Features: The envelope representation of the sequence.
        """
        feature_map = self.get_feature_map(instructions, initial_pitch)
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
    def get_feature_map(cls, instructions: List[InstructionT], initial_pitch: int) -> FeatureMap:
        """Extracts the raw per-dimension feature arrays from an instruction sequence.

        Args:
            instructions: The channel's per-frame instructions.
            initial_pitch: Reference pitch the arpeggio envelope is measured against.

        Returns:
            FeatureMap: The per-dimension arrays for this channel.
        """

    @classmethod
    @abstractmethod
    def derive_initial_pitch(cls, instructions: List[InstructionT]) -> int:
        """Chooses the reference pitch an instruction sequence's arpeggio is measured against.

        The reference is chosen once, when a reconstruction is built, and stored alongside
        the sequence. Every later export measures against that stored value, so editing the
        arpeggio moves the frames around a base pitch that stays put.

        Args:
            instructions: The channel's per-frame instructions.

        Returns:
            int: The reference pitch for the sequence.
        """

    @classmethod
    def from_features(cls, features: Features) -> List[InstructionT]:
        """Rebuilds the instruction sequence from a :class:`Features`.

        Walks the envelopes frame by frame and assembles one instruction per frame. Every
        envelope is read relative to itself — a dimension trimmed shorter than the sequence
        holds its own final value over the remaining frames — so the arpeggio stays an
        offset from ``initial_pitch`` for the whole sequence.

        Args:
            features: The envelope representation of a channel.

        Returns:
            List[InstructionT]: The reconstructed per-frame instructions.
        """
        initial_pitch = features.initial_pitch
        envelopes: Dict[FeatureKey, np.ndarray] = {
            key: cast(np.ndarray, value)
            for key, value in features.feature_map.items()
            if key != FeatureKey.INITIAL_PITCH and value is not None
        }
        max_length = max((len(array) for array in envelopes.values()), default=0)

        instructions: List[InstructionT] = []
        for index in range(max_length):
            instruction_dictionary: Dict[str, Union[bool, int]] = {}
            for key, array in envelopes.items():
                attribute = cls._remap_feature_key(key)
                if not attribute:
                    continue

                instruction_dictionary[attribute] = int(hold(array, index, default=EMPTY_ENVELOPE_VALUE))

            instructions.append(cls._features_dictionary_to_instruction(instruction_dictionary, initial_pitch))

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
    def _remap_feature_key(cls, feature_key: FeatureKey) -> Optional[InstructionFields]:
        if not hasattr(cls, "_ATTRIBUTE_MAP"):
            raise NotImplementedError("Subclasses must define _ATTRIBUTE_MAP")

        return cls._ATTRIBUTE_MAP.get(feature_key)

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
