from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Final

from sampletones_core.constants.enums import FeatureKey, GeneratorName


@dataclass(frozen=True)
class Block:
    """A FamiTracker module block identity: its name and format version."""

    name: str
    version: int


class ChannelId(IntEnum):
    """Channel identifiers stored in the HEADER block and order table."""

    SQUARE1 = 0
    SQUARE2 = 1
    TRIANGLE = 2
    NOISE = 3
    DPCM = 4


class SequenceKind(IntEnum):
    """The five 2A03 instrument sequence dimensions, in FamiTracker slot order."""

    VOLUME = 0
    ARPEGGIO = 1
    PITCH = 2
    HI_PITCH = 3
    DUTY = 4


class NoteValue(IntEnum):
    """Reserved values of a pattern cell's note column.

    Pitched notes occupy ``1``..``12`` (C..B); the values below are the non-pitched
    markers.
    """

    NONE = 0
    C = 1
    B = 12
    RELEASE = 13
    HALT = 14


class Machine(IntEnum):
    """Playback machine stored in the PARAMS block."""

    NTSC = 0
    PAL = 1


# File-level: module
FTM_MAGIC: Final[bytes] = b"FamiTracker Module"
FTM_VERSION: Final[int] = 0x0440
FTM_END_MARKER: Final[bytes] = b"END"
BLOCK_NAME_LENGTH: Final[int] = 16
INFO_STRING_LENGTH: Final[int] = 32

# File-level: instrument
FTI_MAGIC: Final[bytes] = b"FTI"
FTI_VERSION: Final[bytes] = b"2.4"

# Instrument
INSTRUMENT_TYPE_2A03: Final[int] = 1
SEQUENCE_COUNT_2A03: Final[int] = 5
MAX_INSTRUMENTS: Final[int] = 64
MAX_SEQUENCES_PER_TYPE: Final[int] = 128

# DPCM key-assignment table geometry (empty by design)
NOTE_RANGE: Final[int] = 12
OCTAVE_RANGE: Final[int] = 8
DPCM_KEY_ASSIGNMENTS: Final[int] = NOTE_RANGE * OCTAVE_RANGE

# Pattern cell sentinels
EMPTY_NOTE: Final[int] = 0
EMPTY_INSTRUMENT: Final[int] = 0x40
EMPTY_VOLUME: Final[int] = 0x10
EMPTY_EFFECT: Final[int] = 0
DEFAULT_EFFECT_COLUMNS: Final[int] = 1

# Note-cell octave range
MIN_OCTAVE: Final[int] = 0
MAX_OCTAVE: Final[int] = 7

# Sequence framing
NO_LOOP_POINT: Final[int] = -1
NO_RELEASE_POINT: Final[int] = -1
DEFAULT_SEQUENCE_SETTING: Final[int] = 0
LOOP_FROM_START: Final[int] = 0

# PARAMS defaults
EXPANSION_NONE: Final[int] = 0
CHANNEL_COUNT_2A03: Final[int] = 5
DEFAULT_VIBRATO_STYLE: Final[int] = 1
DEFAULT_HIGHLIGHT_FIRST: Final[int] = 4
DEFAULT_HIGHLIGHT_SECOND: Final[int] = 16
ENGINE_SPEED_MACHINE_DEFAULT: Final[int] = 0
NTSC_FREQUENCY: Final[int] = 60
PAL_FREQUENCY: Final[int] = 50
SINGLE_TRACK_COUNT: Final[int] = 1

# Comment display-on-open flag
COMMENT_HIDDEN_ON_OPEN: Final[int] = 0

# Block identities (name, version) — vanilla FamiTracker 0.4.6
BLOCK_PARAMS: Final[Block] = Block("PARAMS", 6)
BLOCK_INFO: Final[Block] = Block("INFO", 1)
BLOCK_HEADER: Final[Block] = Block("HEADER", 3)
BLOCK_INSTRUMENTS: Final[Block] = Block("INSTRUMENTS", 6)
BLOCK_SEQUENCES: Final[Block] = Block("SEQUENCES", 6)
BLOCK_FRAMES: Final[Block] = Block("FRAMES", 3)
BLOCK_PATTERNS: Final[Block] = Block("PATTERNS", 5)
BLOCK_DPCM_SAMPLES: Final[Block] = Block("DPCM SAMPLES", 1)
BLOCK_COMMENTS: Final[Block] = Block("COMMENTS", 1)

GENERATOR_NAME_TO_CHANNEL_ID: Final[Dict[GeneratorName, ChannelId]] = {
    GeneratorName.PULSE1: ChannelId.SQUARE1,
    GeneratorName.PULSE2: ChannelId.SQUARE2,
    GeneratorName.TRIANGLE: ChannelId.TRIANGLE,
    GeneratorName.NOISE: ChannelId.NOISE,
}

FEATURE_KEY_TO_SEQUENCE_KIND: Final[Dict[FeatureKey, SequenceKind]] = {
    FeatureKey.VOLUME: SequenceKind.VOLUME,
    FeatureKey.ARPEGGIO: SequenceKind.ARPEGGIO,
    FeatureKey.PITCH: SequenceKind.PITCH,
    FeatureKey.HI_PITCH: SequenceKind.HI_PITCH,
    FeatureKey.DUTY_CYCLE: SequenceKind.DUTY,
}
