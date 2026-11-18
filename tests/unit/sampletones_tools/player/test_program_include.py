from typing import Dict, Final

import pytest

from sampletones_player.specification.program import (
    ARTIST_COLUMNS,
    ARTIST_OFFSET,
    CLOCK_DIGITS,
    COPYRIGHT_COLUMNS,
    COPYRIGHT_OFFSET,
    DIGIT_BASE,
    FRAME_COUNT_SIZE,
    LINKED_SONG_OFFSET,
    LOOP_FRAMES_OFFSET,
    LOOP_PROGRESS_OFFSET,
    LOOP_SECOND_OFFSET,
    LOOP_TIME_OFFSET,
    PROGRAM_BLOCK_SIZE,
    PROGRESS_PIXELS,
    PROGRESS_STEP_OFFSET,
    SECOND_STEP,
    TITLE_COLUMNS,
    TITLE_OFFSET,
    TOTAL_FRAMES_OFFSET,
    TOTAL_TIME_OFFSET,
    UNWRITTEN_BYTE,
)
from sampletones_tools.player.assembler.layout import ASSEMBLY_DIRECTORY, INCLUDE_DIRECTORY
from tests.unit.sampletones_tools.player.equates import read_equates

PROGRAM_INCLUDE: Final[str] = "program.inc"

STATED: Final[Dict[str, int]] = {
    "TITLE_COLUMNS": TITLE_COLUMNS,
    "ARTIST_COLUMNS": ARTIST_COLUMNS,
    "COPYRIGHT_COLUMNS": COPYRIGHT_COLUMNS,
    "CLOCK_DIGITS": CLOCK_DIGITS,
    "FRAME_COUNT_SIZE": FRAME_COUNT_SIZE,
    "LINKED_SONG_OFFSET": LINKED_SONG_OFFSET,
    "TITLE_OFFSET": TITLE_OFFSET,
    "ARTIST_OFFSET": ARTIST_OFFSET,
    "COPYRIGHT_OFFSET": COPYRIGHT_OFFSET,
    "TOTAL_TIME_OFFSET": TOTAL_TIME_OFFSET,
    "TOTAL_FRAMES_OFFSET": TOTAL_FRAMES_OFFSET,
    "PROGRESS_STEP_OFFSET": PROGRESS_STEP_OFFSET,
    "LOOP_FRAMES_OFFSET": LOOP_FRAMES_OFFSET,
    "LOOP_TIME_OFFSET": LOOP_TIME_OFFSET,
    "LOOP_SECOND_OFFSET": LOOP_SECOND_OFFSET,
    "LOOP_PROGRESS_OFFSET": LOOP_PROGRESS_OFFSET,
    "PROGRAM_BLOCK_SIZE": PROGRAM_BLOCK_SIZE,
    "SECOND_STEP": SECOND_STEP,
    "PROGRESS_PIXELS": PROGRESS_PIXELS,
    "DIGIT_BASE": DIGIT_BASE,
    "UNWRITTEN_BYTE": UNWRITTEN_BYTE,
}


@pytest.fixture(name="equates", scope="module")
def equates_fixture() -> Dict[str, int]:
    return read_equates(ASSEMBLY_DIRECTORY / INCLUDE_DIRECTORY / PROGRAM_INCLUDE)


class TestTheShellReadsTheBlockTheExporterWrites:
    """Every figure the shell reads the program block by, held against the specification."""

    @pytest.mark.parametrize("name", sorted(STATED), ids=sorted(STATED))
    def test_the_include_states_what_the_specification_states(self, name: str, equates: Dict[str, int]) -> None:
        assert equates[name] == STATED[name]
