from typing import Final

from sampletones_core.constants.enums import ChannelName

WORD_SIZE: Final[int] = 2

STEP_WHOLE_OFFSET: Final[int] = 0
STEP_FRACTION_OFFSET: Final[int] = STEP_WHOLE_OFFSET + 1
TOTAL_TICKS_OFFSET: Final[int] = STEP_FRACTION_OFFSET + WORD_SIZE
LOOP_TICK_OFFSET: Final[int] = TOTAL_TICKS_OFFSET + WORD_SIZE
STREAM_OFFSETS_OFFSET: Final[int] = LOOP_TICK_OFFSET + WORD_SIZE
SONG_HEADER_SIZE: Final[int] = STREAM_OFFSETS_OFFSET + WORD_SIZE * len(ChannelName)

NO_LOOP: Final[int] = 0xFFFF
MAX_STREAM_OFFSET: Final[int] = 0xFFFF
