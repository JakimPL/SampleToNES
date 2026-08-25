from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Generic, Iterable, List, Optional, Tuple, Union

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.features import CHANNEL_FEATURE_DEFAULTS
from sampletones_core.features.envelope import Envelope
from sampletones_core.generators import GeneratorTypeUnion
from sampletones_core.instructions import (
    InstructionFields,
    InstructionT,
    InstructionTypeUnion,
)

from .feature import Features


def _sounding_length(volume: Tuple[int, ...]) -> Optional[int]:
    """How far every dimension is kept: one frame past the last the volume sounds at.

    The frame past the last audible one is what releases a note, so a reconstruction that runs
    out while still loud is kept together with the silence its generator wrote after it.

    Args:
        volume: The per-tick volume the channel wrote.

    Returns:
        Optional[int]: The item count to keep, or ``None`` where the channel never sounds and
            every dimension stands as written.
    """
    audible = [index for index, level in enumerate(volume) if level]
    if not audible:
        return None

    return audible[-1] + 2


def _trimmed(items: Tuple[int, ...]) -> Tuple[int, ...]:
    """One dimension with its repeated tail dropped, keeping one instance of its final value.

    Args:
        items: The values the dimension wrote.

    Returns:
        Tuple[int, ...]: The values up to and including the last one that changes.
    """
    if not items:
        return items

    length = len(items)
    while length > 1 and items[length - 1] == items[length - 2]:
        length -= 1

    return items[:length]


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

    @classmethod
    def to_features(
        cls,
        instructions: List[InstructionT],
        initial_pitch: int,
        held_features: Iterable[FeatureKey],
    ) -> Features:
        """Converts an instruction sequence into its :class:`Features`.

        An instruction states every dimension of its frame, so the dimensions the instrument
        leaves to the channel are named alongside the sequence and come back with empty
        envelopes: what the frames carry for them is the value the channel held. Every dimension
        is trimmed to the span ending just after the last audible frame, which is what leaves a
        reconstruction resting at silence once its volume runs out.

        Args:
            instructions: The channel's per-frame instructions.
            initial_pitch: Reference pitch the arpeggio envelope is measured against.
            held_features: The dimensions the channel governs.

        Returns:
            Features: The envelope representation of the sequence.
        """
        written = cls.read_envelopes(instructions, initial_pitch)
        sounding = _sounding_length(written.get(FeatureKey.VOLUME, ()))
        envelopes = {
            feature_key: Envelope[int](items=_trimmed(items[:sounding])) for feature_key, items in written.items()
        }
        return Features.of(initial_pitch, envelopes).leave_to_channel(held_features)

    @classmethod
    @abstractmethod
    def unstated_features(cls, instructions: List[InstructionT]) -> Tuple[FeatureKey, ...]:
        """The dimensions this stream leaves to the channel rather than writing itself.

        A stream states every dimension its frames carry a choice for. Where a dimension carries
        nothing but the value a channel holds from the start of a song, the stream has made no
        choice at all, and saying so leaves the dimension empty rather than pinning it to a value
        it would sound at anyway.

        Args:
            instructions: The channel's per-frame instructions.

        Returns:
            Tuple[FeatureKey, ...]: The dimensions the channel governs, in dimension order.
        """

    @classmethod
    @abstractmethod
    def read_envelopes(
        cls,
        instructions: List[InstructionT],
        initial_pitch: int,
    ) -> Dict[FeatureKey, Tuple[int, ...]]:
        """The per-tick values each dimension this channel reads carries.

        Args:
            instructions: The channel's per-frame instructions.
            initial_pitch: Reference pitch the arpeggio values are measured against.

        Returns:
            Dict[FeatureKey, Tuple[int, ...]]: The values per dimension the generator offers.
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
        envelopes = features.envelopes

        instructions: List[InstructionT] = []
        for index in range(features.frame_count):
            instruction_dictionary: Dict[str, Union[bool, int]] = {}
            for feature_key, envelope in envelopes.items():
                attribute = cls._remap_feature_key(feature_key)
                if not attribute:
                    continue

                item = envelope.at(index)
                instruction_dictionary[attribute] = item if item is not None else CHANNEL_FEATURE_DEFAULTS[feature_key]

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

        written = cls.read_envelopes([instruction], initial_pitch)
        return {feature_key: items[0] for feature_key, items in written.items() if items}

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
