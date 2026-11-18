from typing import Final

import pytest

from sampletones_player.information import ProgramInformation
from sampletones_player.rom.clock import ProgramClock
from sampletones_player.rom.program import SCREEN_TEXT, program_block, screen_line
from sampletones_player.specification.program import (
    ARTIST_COLUMNS,
    ARTIST_OFFSET,
    COPYRIGHT_COLUMNS,
    COPYRIGHT_OFFSET,
    LOOP_FRAMES_OFFSET,
    LOOP_TIME_OFFSET,
    PROGRAM_BLOCK_SIZE,
    TITLE_COLUMNS,
    TITLE_OFFSET,
    TOTAL_FRAMES_OFFSET,
    TOTAL_TIME_OFFSET,
)
from tests.suite.base import BaseTestSuite

SONG_ADDRESS: Final[int] = 0x8316
CLOCK: Final[ProgramClock] = ProgramClock(total_frames=0x012345, loop_frame=0x000100)
INFORMATION: Final[ProgramInformation] = ProgramInformation(title="Żółw", artist="Łukasz", copyright="© 2026")
FIELD_WIDTH: Final[int] = 6


def field(block: bytes, offset: int, columns: int) -> str:
    return block[offset : offset + columns].decode("ascii")


class TestAScreenLine(BaseTestSuite):
    def test_a_short_line_is_padded_with_blank_cells(self) -> None:
        assert screen_line("Amen", FIELD_WIDTH) == b"Amen  "

    def test_a_character_the_font_leaves_out_shows_as_a_question_mark(self) -> None:
        assert screen_line("A\tB", FIELD_WIDTH) == b"A?B   "

    def test_a_line_longer_than_its_field_is_refused(self) -> None:
        with pytest.raises(ValueError, match=str(FIELD_WIDTH)):
            screen_line("x" * (FIELD_WIDTH + 1), FIELD_WIDTH)


class TestTheProgramBlock(BaseTestSuite):
    def test_it_takes_the_size_the_shell_reads(self) -> None:
        assert len(program_block(SONG_ADDRESS, INFORMATION, CLOCK)) == PROGRAM_BLOCK_SIZE

    def test_it_opens_with_the_song_address(self) -> None:
        assert program_block(SONG_ADDRESS, INFORMATION, CLOCK)[:2] == SONG_ADDRESS.to_bytes(2, "little")

    def test_each_line_is_folded_to_the_font_and_padded_to_its_field(self) -> None:
        block = program_block(SONG_ADDRESS, INFORMATION, CLOCK)

        assert field(block, TITLE_OFFSET, TITLE_COLUMNS) == "Zolw".ljust(TITLE_COLUMNS)
        assert field(block, ARTIST_OFFSET, ARTIST_COLUMNS) == "Lukasz".ljust(ARTIST_COLUMNS)
        assert field(block, COPYRIGHT_OFFSET, COPYRIGHT_COLUMNS) == "? 2026".ljust(COPYRIGHT_COLUMNS)

    def test_a_long_title_is_cut_at_its_field(self) -> None:
        long = INFORMATION.model_copy(update={"title": "x" * (TITLE_COLUMNS + 5)})

        assert field(program_block(SONG_ADDRESS, long, CLOCK), TITLE_OFFSET, TITLE_COLUMNS) == "x" * TITLE_COLUMNS

    def test_the_counts_are_written_low_byte_first(self) -> None:
        block = program_block(SONG_ADDRESS, INFORMATION, CLOCK)

        assert block[TOTAL_FRAMES_OFFSET : TOTAL_FRAMES_OFFSET + 3] == bytes((0x45, 0x23, 0x01))
        assert block[LOOP_FRAMES_OFFSET : LOOP_FRAMES_OFFSET + 3] == CLOCK.loop_frames.to_bytes(3, "little")

    def test_the_times_are_written_as_their_digits(self) -> None:
        block = program_block(SONG_ADDRESS, INFORMATION, CLOCK)

        assert tuple(block[TOTAL_TIME_OFFSET : TOTAL_TIME_OFFSET + 4]) == CLOCK.total_time
        assert tuple(block[LOOP_TIME_OFFSET : LOOP_TIME_OFFSET + 4]) == CLOCK.loop_time

    def test_every_line_of_the_screen_folds(self) -> None:
        assert all(line.folded for line in (SCREEN_TEXT.title, SCREEN_TEXT.artist, SCREEN_TEXT.copyright))
