from typing import Final

from sampletones_core.formats.famitracker.specification.patterns import NOTE_RANGE, OCTAVE_RANGE

INSTRUMENT_TYPE_2A03: Final[int] = 1
MAX_INSTRUMENTS: Final[int] = 64

STANDALONE_INSTRUMENT_INDEX: Final[int] = 0

DPCM_KEY_ASSIGNMENTS: Final[int] = NOTE_RANGE * OCTAVE_RANGE

DPCM_KEY_BYTES: Final[int] = 3
EMPTY_DPCM_ASSIGNMENTS: Final[int] = 0
EMPTY_DPCM_SAMPLES: Final[int] = 0
