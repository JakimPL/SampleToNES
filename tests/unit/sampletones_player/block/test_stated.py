import struct
from typing import Final, Optional

import pytest

from sampletones_player.block.song import song_to_bytes
from sampletones_player.block.stated import StatedSong
from sampletones_player.specification.song import (
    LOOP_TICK_OFFSET,
    NO_LOOP,
    STEP_FRACTION_OFFSET,
    STEP_WHOLE_OFFSET,
    TOTAL_TICKS_OFFSET,
)
from sampletones_shared.exceptions.validation import TruncatedDataError
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_REFERENCE_TIMER,
    player_song,
    pulse_tick,
    resting_streams,
)

PROGRAM_AREA_BYTES: Final[int] = 0x8000
SOUNDING_TICKS: Final[int] = 7


class TestTheSongABlockStates:
    """A block read back states the clock, the length and the loop its song was written with."""

    @pytest.mark.parametrize("loop_tick", [None, 3], ids=["no loop", "a loop"])
    @pytest.mark.parametrize("nes_frequency", [60, 37], ids=["a whole step", "a fractional step"])
    def test_the_header_reads_back_as_the_song(self, loop_tick: Optional[int], nes_frequency: int) -> None:
        song = player_song(
            resting_streams((pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER),) * SOUNDING_TICKS),
            nes_frequency,
            loop_tick=loop_tick,
        )

        stated = StatedSong.read(song_to_bytes(song, PROGRAM_AREA_BYTES))

        assert stated == StatedSong(
            step=song.schedule.fixed_point_step.value,
            ticks=song.ticks,
            loop_tick=NO_LOOP if loop_tick is None else loop_tick,
        )

    def test_the_fields_stand_where_the_specification_places_them(self) -> None:
        block = bytearray(LOOP_TICK_OFFSET + 2)
        block[STEP_WHOLE_OFFSET] = 2
        struct.pack_into("<H", block, STEP_FRACTION_OFFSET, 0x8001)
        struct.pack_into("<H", block, TOTAL_TICKS_OFFSET, 0x1234)
        struct.pack_into("<H", block, LOOP_TICK_OFFSET, 0x0102)

        assert StatedSong.read(bytes(block)) == StatedSong(step=0x28001, ticks=0x1234, loop_tick=0x0102)

    @pytest.mark.parametrize("length", [0, 1, LOOP_TICK_OFFSET + 1])
    def test_a_block_ending_inside_its_header_is_refused(self, length: int) -> None:
        with pytest.raises(TruncatedDataError):
            StatedSong.read(bytes(length))
