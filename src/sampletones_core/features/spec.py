from dataclasses import dataclass
from typing import Dict, Final, List, Tuple

from sampletones_core.constants.enums import ChannelName, FeatureKey, LibraryGeneratorName
from sampletones_core.constants.general import (
    ARPEGGIO_MAX,
    ARPEGGIO_MIN,
    MAX_DUTY_CYCLE,
    MAX_NOISE_MODE,
    MAX_PERIOD,
    MAX_VOLUME,
    NUM_PERIODS,
)


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


CHANNEL_FEATURE_DEFAULTS: Final[Dict[FeatureKey, int]] = {
    FeatureKey.VOLUME: MAX_VOLUME,
    FeatureKey.ARPEGGIO: 0,
    FeatureKey.PITCH: 0,
    FeatureKey.HI_PITCH: 0,
    FeatureKey.DUTY_CYCLE: 0,
}


RESTING_REFERENCE_PITCH: Final[int] = 60
RESTING_REFERENCE_PERIOD: Final[int] = NUM_PERIODS // 2


GENERATOR_FEATURE_RANGES: Final[Dict[LibraryGeneratorName, Dict[FeatureKey, FeatureRange]]] = {
    LibraryGeneratorName.PULSE: {
        FeatureKey.VOLUME: FeatureRange(0, MAX_VOLUME),
        FeatureKey.ARPEGGIO: FeatureRange(ARPEGGIO_MIN, ARPEGGIO_MAX),
        FeatureKey.DUTY_CYCLE: FeatureRange(0, MAX_DUTY_CYCLE),
    },
    LibraryGeneratorName.TRIANGLE: {
        FeatureKey.VOLUME: FeatureRange(0, MAX_VOLUME),
        FeatureKey.ARPEGGIO: FeatureRange(ARPEGGIO_MIN, ARPEGGIO_MAX),
    },
    LibraryGeneratorName.NOISE: {
        FeatureKey.VOLUME: FeatureRange(0, MAX_VOLUME),
        FeatureKey.ARPEGGIO: FeatureRange(0, MAX_PERIOD),
        FeatureKey.DUTY_CYCLE: FeatureRange(0, MAX_NOISE_MODE),
    },
}


CHANNEL_GENERATOR_KIND: Final[Dict[ChannelName, LibraryGeneratorName]] = {
    ChannelName.PULSE1: LibraryGeneratorName.PULSE,
    ChannelName.PULSE2: LibraryGeneratorName.PULSE,
    ChannelName.TRIANGLE: LibraryGeneratorName.TRIANGLE,
    ChannelName.NOISE: LibraryGeneratorName.NOISE,
}


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
    match CHANNEL_GENERATOR_KIND[channel_name]:
        case LibraryGeneratorName.NOISE:
            return RESTING_REFERENCE_PERIOD
        case _:
            return RESTING_REFERENCE_PITCH


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
    kind: LibraryGeneratorName,
) -> List[FeatureKey]:
    ranges = GENERATOR_FEATURE_RANGES[kind]
    return [feature for feature in FEATURE_DIMENSION_ORDER if feature in ranges]


def feature_range(
    kind: LibraryGeneratorName,
    feature: FeatureKey,
) -> FeatureRange:
    return GENERATOR_FEATURE_RANGES[kind][feature]


def supports(kind: LibraryGeneratorName, feature: FeatureKey) -> bool:
    return feature in GENERATOR_FEATURE_RANGES[kind]
