from dataclasses import dataclass
from typing import Dict, Final, FrozenSet, List, Tuple

from sampletones_core.constants.enums import ChannelName, FeatureKey, GeneratorName
from sampletones_core.constants.general import (
    ARPEGGIO_MAX,
    ARPEGGIO_MIN,
    MAX_DUTY_CYCLE,
    MAX_NOISE_MODE,
    MAX_PERIOD,
    MAX_VOLUME,
    NUM_PERIODS,
    PITCH_BEND_MAX,
    PITCH_BEND_MIN,
)
from sampletones_core.utils.frequencies import transpose_period, transpose_pitch


@dataclass(frozen=True)
class FeatureRange:
    minimum: int
    maximum: int


FEATURE_DIMENSION_ORDER: Final[Tuple[FeatureKey, ...]] = (
    FeatureKey.VOLUME,
    FeatureKey.ARPEGGIO,
    FeatureKey.PITCH,
    FeatureKey.HI_PITCH,
    FeatureKey.DUTY_CYCLE,
)


BEND_FEATURES: Final[Tuple[FeatureKey, ...]] = (
    FeatureKey.PITCH,
    FeatureKey.HI_PITCH,
)


CHANNEL_FEATURE_DEFAULTS: Final[Dict[FeatureKey, int]] = {
    FeatureKey.VOLUME: MAX_VOLUME,
    FeatureKey.ARPEGGIO: 0,
    FeatureKey.PITCH: 0,
    FeatureKey.HI_PITCH: 0,
    FeatureKey.DUTY_CYCLE: 0,
}


RESTING_REFERENCE_PITCH: Final[int] = 60
RESTING_REFERENCE_PERIOD: Final[int] = NUM_PERIODS // 2


GENERATOR_FEATURE_RANGES: Final[Dict[GeneratorName, Dict[FeatureKey, FeatureRange]]] = {
    GeneratorName.PULSE: {
        FeatureKey.VOLUME: FeatureRange(0, MAX_VOLUME),
        FeatureKey.ARPEGGIO: FeatureRange(ARPEGGIO_MIN, ARPEGGIO_MAX),
        FeatureKey.PITCH: FeatureRange(PITCH_BEND_MIN, PITCH_BEND_MAX),
        FeatureKey.HI_PITCH: FeatureRange(PITCH_BEND_MIN, PITCH_BEND_MAX),
        FeatureKey.DUTY_CYCLE: FeatureRange(0, MAX_DUTY_CYCLE),
    },
    GeneratorName.TRIANGLE: {
        FeatureKey.VOLUME: FeatureRange(0, MAX_VOLUME),
        FeatureKey.ARPEGGIO: FeatureRange(ARPEGGIO_MIN, ARPEGGIO_MAX),
        FeatureKey.PITCH: FeatureRange(PITCH_BEND_MIN, PITCH_BEND_MAX),
        FeatureKey.HI_PITCH: FeatureRange(PITCH_BEND_MIN, PITCH_BEND_MAX),
    },
    GeneratorName.NOISE: {
        FeatureKey.VOLUME: FeatureRange(0, MAX_VOLUME),
        FeatureKey.ARPEGGIO: FeatureRange(0, MAX_PERIOD),
        FeatureKey.DUTY_CYCLE: FeatureRange(0, MAX_NOISE_MODE),
    },
}


CHANNEL_GENERATOR_KIND: Final[Dict[ChannelName, GeneratorName]] = {
    ChannelName.PULSE1: GeneratorName.PULSE,
    ChannelName.PULSE2: GeneratorName.PULSE,
    ChannelName.TRIANGLE: GeneratorName.TRIANGLE,
    ChannelName.NOISE: GeneratorName.NOISE,
}

GENERATOR_CHANNEL_KINDS: Final[Dict[GeneratorName, FrozenSet[ChannelName]]] = {
    GeneratorName.PULSE: frozenset((ChannelName.PULSE1, ChannelName.PULSE2)),
    GeneratorName.TRIANGLE: frozenset((ChannelName.TRIANGLE,)),
    GeneratorName.NOISE: frozenset((ChannelName.NOISE,)),
}


def generator_channel(generator_name: GeneratorName) -> ChannelName:
    """The channel that stands for a generator, which is the first one it drives.

    A generator drives one channel or two, and the two pulse channels read an instrument the same
    way, so naming a generator names a channel to sound it on. Reading the channels in channel
    order keeps the answer the same on every call.

    Args:
        generator_name: The generator being resolved.

    Returns:
        ChannelName: The channel that generator is heard on.
    """
    channels = GENERATOR_CHANNEL_KINDS[generator_name]
    return next(channel_name for channel_name in ChannelName.items() if channel_name in channels)


def speaks_in_periods(channel_name: ChannelName) -> bool:
    """Whether this channel reads a pitch-like value as a noise period rather than a semitone.

    The noise channel selects one of sixteen periods where the others name a note, so every rule
    that reads a pitch — a reference, a note name, a transpose — turns on this one answer.

    Args:
        channel_name: The channel being read.

    Returns:
        bool: Whether the channel speaks in noise periods.
    """
    return CHANNEL_GENERATOR_KIND[channel_name] is GeneratorName.NOISE


def channel_reference(
    channel_name: ChannelName,
    *,
    pitch: int,
    period: int,
) -> int:
    """Which of a pitch-and-period pair a channel measures its arpeggio against.

    An arpeggio envelope is a semitone offset on the tonal channels and a period offset on noise,
    so a reference is stated as both and the channel picks the one it reads. Every voice states
    its reference this way, which is what lets one voice be started on any channel.

    Args:
        channel_name: The channel reading the reference.
        pitch: The reference a tonal channel measures against.
        period: The reference the noise channel measures against.

    Returns:
        int: The reference this channel reads.
    """
    return period if speaks_in_periods(channel_name) else pitch


def transposed_reference(
    channel_name: ChannelName,
    reference: int,
    transpose: int,
) -> int:
    """Where a voice sounds on one channel once a row's transpose has moved it.

    This is the pitch the channel plays, so a grid printing a note and a channel sounding one
    arrive at the same value: a tonal channel is held inside the range it plays, and the noise
    channel walks around the sixteen periods the hardware offers.

    Args:
        channel_name: The channel sounding the voice.
        reference: The value the voice is measured against on this channel.
        transpose: The semitones the row has reached.

    Returns:
        int: The pitch, or the period, the channel sounds.
    """
    if speaks_in_periods(channel_name):
        return transpose_period(reference, transpose)

    return transpose_pitch(reference, transpose)


def resting_reference(channel_name: ChannelName) -> int:
    """The reference an arpeggio envelope is measured against while a channel describes no frame.

    A channel with no frames still carries a reference, since the first envelope given to it
    sounds every frame at that value. Resting mid-range puts a channel added by hand on an
    audible note, and on a noise period between the extremes.

    Args:
        channel_name: The channel whose resting reference is read.

    Returns:
        int: The pitch a tonal channel rests at, or the period the noise channel rests at.
    """
    return channel_reference(
        channel_name,
        pitch=RESTING_REFERENCE_PITCH,
        period=RESTING_REFERENCE_PERIOD,
    )


def resting_held_features(
    channel_name: ChannelName,
) -> Tuple[FeatureKey, ...]:
    """The dimensions a channel governs while it describes no frame.

    A stream with no frames writes no dimension, so every dimension the channel offers is the
    channel's to hold. Recording them makes a channel that has always stood by read the same as
    one edited down to empty envelopes.

    Args:
        channel_name: The channel whose resting record is read.

    Returns:
        Tuple[FeatureKey, ...]: The dimensions the channel offers, in dimension order.
    """
    return tuple(supported_features(CHANNEL_GENERATOR_KIND[channel_name]))


def supported_features(
    kind: GeneratorName,
) -> List[FeatureKey]:
    ranges = GENERATOR_FEATURE_RANGES[kind]
    return [feature for feature in FEATURE_DIMENSION_ORDER if feature in ranges]


def feature_range(
    kind: GeneratorName,
    feature: FeatureKey,
) -> FeatureRange:
    return GENERATOR_FEATURE_RANGES[kind][feature]


def supports(kind: GeneratorName, feature: FeatureKey) -> bool:
    return feature in GENERATOR_FEATURE_RANGES[kind]
