from enum import IntEnum
from typing import Dict, Final

from sampletones_core.constants.enums import FeatureKey


class SequenceKind(IntEnum):
    """The five 2A03 instrument sequence dimensions, in FamiTracker slot order."""

    VOLUME = 0
    ARPEGGIO = 1
    PITCH = 2
    HI_PITCH = 3
    DUTY = 4


SEQUENCE_COUNT_2A03: Final[int] = 5
MAX_SEQUENCES_PER_TYPE: Final[int] = 128
MAX_SEQUENCE_ITEMS: Final[int] = 252

# Sequence framing
NO_LOOP_POINT: Final[int] = -1
NO_RELEASE_POINT: Final[int] = -1
DEFAULT_SEQUENCE_SETTING: Final[int] = 0
LOOP_FROM_START: Final[int] = 0
SEQUENCE_ENABLED: Final[int] = 1
SEQUENCE_DISABLED: Final[int] = 0

FEATURE_KEY_TO_SEQUENCE_KIND: Final[Dict[FeatureKey, SequenceKind]] = {
    FeatureKey.VOLUME: SequenceKind.VOLUME,
    FeatureKey.ARPEGGIO: SequenceKind.ARPEGGIO,
    FeatureKey.PITCH: SequenceKind.PITCH,
    FeatureKey.HI_PITCH: SequenceKind.HI_PITCH,
    FeatureKey.DUTY_CYCLE: SequenceKind.DUTY,
}
