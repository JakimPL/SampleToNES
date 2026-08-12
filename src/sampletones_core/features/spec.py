from dataclasses import dataclass
from typing import Dict, Final, Tuple

from sampletones_core.constants.enums import FeatureKey, GeneratorName, LibraryGeneratorName
from sampletones_core.constants.general import (
    ARPEGGIO_MAX,
    ARPEGGIO_MIN,
    MAX_DUTY_CYCLE,
    MAX_NOISE_MODE,
    MAX_PERIOD,
    MAX_VOLUME,
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


GENERATOR_KIND: Final[Dict[GeneratorName, LibraryGeneratorName]] = {
    GeneratorName.PULSE1: LibraryGeneratorName.PULSE,
    GeneratorName.PULSE2: LibraryGeneratorName.PULSE,
    GeneratorName.TRIANGLE: LibraryGeneratorName.TRIANGLE,
    GeneratorName.NOISE: LibraryGeneratorName.NOISE,
}


def supported_features(kind: LibraryGeneratorName) -> list[FeatureKey]:
    ranges = GENERATOR_FEATURE_RANGES[kind]
    return [feature for feature in FEATURE_DIMENSION_ORDER if feature in ranges]


def feature_range(kind: LibraryGeneratorName, feature: FeatureKey) -> FeatureRange:
    return GENERATOR_FEATURE_RANGES[kind][feature]


def supports(kind: LibraryGeneratorName, feature: FeatureKey) -> bool:
    return feature in GENERATOR_FEATURE_RANGES[kind]
