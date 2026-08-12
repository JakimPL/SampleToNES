from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Generic, Iterable, List, Optional, Union, cast

import numpy as np

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.features import CHANNEL_FEATURE_DEFAULTS
from sampletones_core.generators import GeneratorTypeUnion
from sampletones_core.instructions import (
    InstructionFields,
    InstructionT,
    InstructionTypeUnion,
)
from sampletones_core.types.feature import FeatureMap
from sampletones_shared.utils.arrays import hold, trim

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

    _ATTRIBUTE_MAP: ClassVar[Dict[FeatureKey, InstructionFields]]

    def to_features(
        self,
        instructions: List[InstructionT],
        initial_pitch: int,
        held_features: Iterable[FeatureKey],
    ) -> Features:
        """Converts an instruction sequence into its :class:`Features`.

        An instruction states every dimension of its frame, so the dimensions the instrument
        leaves to the channel are named alongside the sequence and come back with empty
        envelopes: what the frames carry for them is the value the channel held.

        Args:
            instructions: The channel's per-frame instructions.
            initial_pitch: Reference pitch the arpeggio envelope is measured against.
            held_features: The dimensions the channel governs.

        Returns:
            Features: The envelope representation of the sequence.
        """
        feature_map = self.get_feature_map(instructions, initial_pitch)
        features = self.from_feature_map_to_features(feature_map)
        features.leave_to_channel(held_features)
        return features

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
        offset from ``initial_pitch`` for the whole sequence. A dimension the instrument
        leaves to the channel carries no item, and every frame states the value a channel
        holds for it from the start of a song, which is what the sequence sounds like played
        on its own.

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

                instruction_dictionary[attribute] = int(
                    hold(
                        array,
                        index,
                        default=CHANNEL_FEATURE_DEFAULTS[key],
                    )
                )

            instructions.append(cls._features_dictionary_to_instruction(instruction_dictionary, initial_pitch))

        return instructions

    @classmethod
    def feature_values(
        cls,
        instruction: InstructionT,
        initial_pitch: int,
    ) -> Dict[FeatureKey, int]:
        """The envelope values one frame states.

        A frame that sounds states every dimension the channel reads, each in the terms its
        envelope is written in. A silent frame states its level alone, leaving the rest to the
        channel, which is how a sequence holds its pitch and timbre across a rest.

        Reading the frame as a sequence of one is what keeps this the same reading `to_features`
        gives it, so a frame played in a song carries the values its envelopes show.

        Args:
            instruction: The frame to read.
            initial_pitch: Reference pitch the arpeggio value is measured against.

        Returns:
            Dict[FeatureKey, int]: The value the frame states for each dimension it names.
        """
        if not instruction.on:
            return {FeatureKey.VOLUME: 0}

        feature_map = cls.get_feature_map([instruction], initial_pitch)
        return {
            key: int(value[0]) for key, value in feature_map.items() if isinstance(value, np.ndarray) and value.size
        }

    @classmethod
    def instruction_from_values(
        cls,
        values: Dict[FeatureKey, int],
        initial_pitch: int,
    ) -> InstructionT:
        """The frame a row of envelope values describes.

        This is the single-frame form of `from_features`: values arrive in envelope terms and
        come back as the instruction a generator sounds, with the arpeggio measured against
        ``initial_pitch``. Dimensions this channel reads nothing from are passed over, so one
        set of values serves every channel.

        Args:
            values: The value each dimension carries for one frame.
            initial_pitch: Reference pitch the arpeggio value is measured against.

        Returns:
            InstructionT: The frame those values describe.
        """
        dictionary: Dict[str, Union[bool, int]] = {}
        for key, value in values.items():
            attribute = cls._remap_feature_key(key)
            if attribute is not None:
                dictionary[attribute] = value

        return cls._features_dictionary_to_instruction(dictionary, initial_pitch)

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
