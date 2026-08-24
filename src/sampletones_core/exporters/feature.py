from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.features.envelope import Envelope

FeatureEnvelopes = Mapping[FeatureKey, Envelope[int]]


class Features(BaseModel):
    """The per-dimension envelopes describing one FamiTracker instrument.

    Each field is one dimension the channel reads — volume, arpeggio, pitch, hi-pitch and duty
    cycle — carrying the values it writes per tick together with the item they repeat from, beside
    the ``initial_pitch`` the arpeggio is measured against. A dimension the generator offers is an
    envelope, ``None`` for one it lacks; an envelope of no items marks a dimension the instrument
    leaves to the channel, which keeps the value it holds.

    Attributes:
        initial_pitch: Reference pitch the arpeggio envelope is measured against.
        volume: Volume envelope.
        arpeggio: Arpeggio (relative pitch) envelope.
        pitch: Pitch envelope, or ``None`` where the generator lacks the dimension.
        hi_pitch: Fine-pitch envelope, or ``None`` where the generator lacks the dimension.
        duty_cycle: Duty-cycle envelope, or ``None`` where the generator lacks the dimension.
    """

    model_config = ConfigDict(frozen=True)

    initial_pitch: int
    volume: Envelope[int]
    arpeggio: Envelope[int]
    pitch: Optional[Envelope[int]]
    hi_pitch: Optional[Envelope[int]]
    duty_cycle: Optional[Envelope[int]]

    @classmethod
    def of(
        cls,
        initial_pitch: int,
        envelopes: FeatureEnvelopes,
    ) -> Features:
        """The features a channel's dimensions describe, leaving out the ones it lacks.

        Args:
            initial_pitch: Reference pitch the arpeggio envelope is measured against.
            envelopes: The dimensions the generator offers, keyed by the feature they carry.

        Returns:
            Features: Those dimensions, with the generator's missing ones absent.
        """
        return cls(
            initial_pitch=initial_pitch,
            volume=envelopes.get(FeatureKey.VOLUME, Envelope[int]()),
            arpeggio=envelopes.get(FeatureKey.ARPEGGIO, Envelope[int]()),
            pitch=envelopes.get(FeatureKey.PITCH),
            hi_pitch=envelopes.get(FeatureKey.HI_PITCH),
            duty_cycle=envelopes.get(FeatureKey.DUTY_CYCLE),
        )

    @property
    def envelopes(self) -> Dict[FeatureKey, Envelope[int]]:
        """The dimensions this channel offers, keyed by the feature each carries."""
        offered = {
            FeatureKey.VOLUME: self.volume,
            FeatureKey.ARPEGGIO: self.arpeggio,
            FeatureKey.PITCH: self.pitch,
            FeatureKey.HI_PITCH: self.hi_pitch,
            FeatureKey.DUTY_CYCLE: self.duty_cycle,
        }
        return {feature_key: envelope for feature_key, envelope in offered.items() if envelope is not None}

    def envelope(self, feature_key: FeatureKey) -> Envelope[int]:
        """The dimension one feature names.

        Args:
            feature_key: The dimension read.

        Returns:
            Envelope[int]: Its values and the item they repeat from.

        Raises:
            KeyError: If the channel's generator lacks that dimension.
        """
        return self.envelopes[feature_key]

    def offers(self, feature_key: FeatureKey) -> bool:
        """Whether the channel's generator reads this dimension at all."""
        return feature_key in self.envelopes

    def with_envelope(self, feature_key: FeatureKey, envelope: Envelope[int]) -> Features:
        """These features with one dimension replaced.

        Args:
            feature_key: The dimension written.
            envelope: What that dimension now carries; empty items leave it to the channel.

        Returns:
            Features: The features carrying ``envelope`` for ``feature_key``.

        Raises:
            KeyError: If the channel's generator lacks that dimension.
        """
        if not self.offers(feature_key):
            raise KeyError(feature_key)

        return self.model_copy(update={feature_key.value: envelope})

    def leave_to_channel(self, feature_keys: Iterable[FeatureKey]) -> Features:
        """These features with each named dimension emptied, so the channel governs it.

        The dimensions a channel offers are the ones it can hold a value for, so this acts on
        those and leaves the shape of the features as the channel defines it.

        Args:
            feature_keys: The dimensions the instrument leaves to the channel.

        Returns:
            Features: The features with those dimensions carrying no item.
        """
        emptied = {feature_key.value: Envelope[int]() for feature_key in feature_keys if self.offers(feature_key)}
        return self.model_copy(update=emptied)

    @property
    def frame_count(self) -> int:
        """The frame count the envelopes describe, taken from the longest populated dimension."""
        return max((len(envelope.items) for envelope in self.envelopes.values()), default=0)

    @property
    def has_frames(self) -> bool:
        """Whether the envelopes describe a frame, which is what a channel plays.

        Every dimension left to the channel leaves an instrument describing nothing, so this
        is what tells a channel that sounds from one that stands by: an export writes the
        instruments that have frames, and the driver stores only those.
        """
        return self.frame_count > 0

    @property
    def held_features(self) -> Tuple[FeatureKey, ...]:
        """The dimensions the channel governs, whose envelopes carry no item.

        An instrument writes the dimensions it describes and leaves the rest to the channel,
        which keeps the value it already holds for as long as the instrument sounds. These
        are the dimensions it leaves, listed in the order the model declares them.
        """
        return tuple(feature_key for feature_key, envelope in self.envelopes.items() if not envelope.written)


def playing_channels(channels: Mapping[ChannelName, Features]) -> FrozenSet[ChannelName]:
    """The channels among ``channels`` whose envelopes describe a frame.

    Describing a frame is what puts a channel in play: those are the ones an export writes, the
    ones a footprint measures and the ones a panel offers, while the rest stand by. Stating the
    rule once has every reader of a channel's envelopes agree on which of them sound.

    Args:
        channels: The envelopes each channel plays.

    Returns:
        FrozenSet[ChannelName]: The channels that sound.
    """
    return frozenset(channel_name for channel_name, features in channels.items() if features.has_frames)
