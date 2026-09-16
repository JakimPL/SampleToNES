from typing import Final

from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.constants.general import (
    MIXER_NOISE,
    MIXER_PULSE,
    MIXER_TRIANGLE,
    QUIETEST_VOLUME_LEVEL,
)

# Input preprocessing

NORMALIZE: Final[bool] = True
QUANTIZE: Final[bool] = False
QUANTIZATION_LEVELS: Final[int] = 32

# Working level

COEFFICIENT_PERCENTILE: Final[float] = 90.0
COEFFICIENT_AUDIBILITY_FLOOR: Final[float] = 1e-3
MINIMUM_AUDIO_LEVEL: Final[float] = 1e-12

# Library creation

MIN_SAMPLE_LENGTH: Final[float] = 0.05
MAX_SAMPLE_LENGTH: Final[float] = 1.0
LIBRARY_PHASES_PER_SAMPLE: Final[int] = 100

# Calculation methods

TRANSFORMATION_GAMMA: Final[int] = 0
MAX_TRANSFORMATION_GAMMA: Final[int] = 100

# Selection and continuity decoding

SINGLE_STATE_LATTICE_WIDTH: Final[int] = 1

# Drive

MIN_DRIVE: Final[float] = 0.1
UNIT_DRIVE: Final[float] = 1.0
MAX_DRIVE: Final[float] = 5.0

# Stems assignment

MIN_STEMS_CHANNEL_CAP: Final[int] = 1
ALL_STEMS_CHANNEL_CAP: Final[int] = len(ChannelName)
DEFAULT_STEMS_HIERARCHY_MODE: Final[HierarchyMode] = HierarchyMode.ROUND_ROBIN
RESTING_STEM_ID: Final[int] = -1
RESTING_FRAME_COST: Final[float] = 0.0
STEM_ACTIVITY_FLOOR: Final[float] = QUIETEST_VOLUME_LEVEL * min(MIXER_PULSE, MIXER_TRIANGLE, MIXER_NOISE)

# Execution

MAX_WORKERS: Final[int] = 6
