from typing import Dict, Final

import pytest

from sampletones_player.compression.pitch import PITCH_COUNT
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.specification.binary import WORD_SIZE
from sampletones_player.specification.compression import (
    BEND_FLAG,
    DEFAULT_COUNT_FLAG,
    OPCODE_SIZE,
    PHRASE_DEFAULT_SIZE,
    PHRASE_ID_ESCAPE,
    PHRASE_ID_MASK,
    PHRASE_LENGTH_SIZE,
    PHRASE_TABLE_COUNT_SIZE,
    PHRASE_TABLE_ENTRY_SIZE,
    PITCH_INDEX_MASK,
    PLANE_STATE_SIZE,
    TOKEN_OPERAND_MASK,
    TOKEN_TAG_MASK,
    TokenTag,
)
from sampletones_player.specification.planes import (
    COUNT_STEP,
    NOISE_CONTROL_FORM,
    NOISE_VALUE_FORM,
    PLANE_COUNT,
    PULSE_CONTROL_FORM,
    SILENT_PITCH_INDEX,
)
from sampletones_player.specification.registers import (
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_SILENT_RELOAD,
    TRIANGLE_SOUNDING_RELOAD,
)
from sampletones_player.specification.song import (
    ABSENT_STREAM,
    LOOP_ENTRIES_OFFSET,
    LOOP_TICK_OFFSET,
    NO_LOOP,
    PHRASE_TABLE_OFFSET,
    STEP_FRACTION_OFFSET,
    STEP_WHOLE_OFFSET,
    STREAM_OFFSETS_OFFSET,
    TIMER_TABLE_OFFSET,
    TOTAL_TICKS_OFFSET,
)
from sampletones_tools.player.assembler.layout import ASSEMBLY_DIRECTORY, INCLUDE_DIRECTORY
from tests.unit.sampletones_tools.player.equates import read_equates

SONG_INCLUDE: Final[str] = "song.inc"

STATED: Final[Dict[str, int]] = {
    "WORD_SIZE": WORD_SIZE,
    "PLANE_COUNT": PLANE_COUNT,
    "STEP_WHOLE_OFFSET": STEP_WHOLE_OFFSET,
    "STEP_FRACTION_OFFSET": STEP_FRACTION_OFFSET,
    "TOTAL_TICKS_OFFSET": TOTAL_TICKS_OFFSET,
    "LOOP_TICK_OFFSET": LOOP_TICK_OFFSET,
    "TIMER_TABLE_OFFSET": TIMER_TABLE_OFFSET,
    "PHRASE_TABLE_OFFSET": PHRASE_TABLE_OFFSET,
    "STREAM_OFFSETS_OFFSET": STREAM_OFFSETS_OFFSET,
    "LOOP_ENTRIES_OFFSET": LOOP_ENTRIES_OFFSET,
    "NO_LOOP": NO_LOOP,
    "ABSENT_STREAM": ABSENT_STREAM,
    "PITCH_COUNT": PITCH_COUNT,
    "BEND_FLAG": BEND_FLAG,
    "PITCH_INDEX_MASK": PITCH_INDEX_MASK,
    "TOKEN_TAG_MASK": TOKEN_TAG_MASK,
    "TOKEN_OPERAND_MASK": TOKEN_OPERAND_MASK,
    "TAG_HOLD": TokenTag.HOLD,
    "TAG_LITERAL": TokenTag.LITERAL,
    "TAG_PHRASE": TokenTag.PHRASE,
    "TAG_TRANSPOSED_PHRASE": TokenTag.TRANSPOSED_PHRASE,
    "OPCODE_SIZE": OPCODE_SIZE,
    "PHRASE_ID_ESCAPE": PHRASE_ID_ESCAPE,
    "PHRASE_TABLE_COUNT_SIZE": PHRASE_TABLE_COUNT_SIZE,
    "PHRASE_TABLE_ENTRY_SIZE": PHRASE_TABLE_ENTRY_SIZE,
    "PHRASE_LENGTH_SIZE": PHRASE_LENGTH_SIZE,
    "PHRASE_DEFAULT_SIZE": PHRASE_DEFAULT_SIZE,
    "DEFAULT_COUNT_FLAG": DEFAULT_COUNT_FLAG,
    "PHRASE_ID_MASK": PHRASE_ID_MASK,
    "PLANE_STATE_SIZE": PLANE_STATE_SIZE,
    "PLANE_STATE_BYTES": PLANE_COUNT * PLANE_STATE_SIZE,
    "COUNT_STEP": COUNT_STEP,
    "SILENT_PITCH_INDEX": SILENT_PITCH_INDEX,
    "TRIANGLE_COUNTER": TRIANGLE_COUNTER_CONTROL,
    "TRIANGLE_SOUNDING": TRIANGLE_SOUNDING_RELOAD,
    "TRIANGLE_SILENT": TRIANGLE_SILENT_RELOAD,
    "PULSE_CONTROL_MASK": PULSE_CONTROL_FORM.value_mask,
    "PULSE_CONTROL_FIXED": PULSE_CONTROL_FORM.value_or,
    "NOISE_CONTROL_MASK": NOISE_CONTROL_FORM.value_mask,
    "NOISE_CONTROL_FIXED": NOISE_CONTROL_FORM.value_or,
    "NOISE_VALUE_MASK": NOISE_VALUE_FORM.value_mask,
    "NOISE_VALUE_FIXED": NOISE_VALUE_FORM.value_or,
}


@pytest.fixture(name="equates", scope="module")
def equates_fixture() -> Dict[str, int]:
    return read_equates(ASSEMBLY_DIRECTORY / INCLUDE_DIRECTORY / SONG_INCLUDE)


class TestTheDriverReadsTheBlockTheExporterWrites:
    """Every figure the assembly reads the song block by, held against the specification."""

    @pytest.mark.parametrize("name", sorted(STATED), ids=sorted(STATED))
    def test_the_include_states_what_the_specification_states(
        self,
        name: str,
        equates: Dict[str, int],
    ) -> None:
        assert equates[name] == STATED[name]

    def test_the_plane_state_fields_fill_the_block_each_plane_holds(
        self,
        equates: Dict[str, int],
    ) -> None:
        """A plane's decoder state is read by field, so the fields cover the block and no more."""
        fields = ("PLANE_SOURCE", "PLANE_PHRASE", "PLANE_PHRASE_TICKS", "PLANE_TOKEN_TICKS")
        stated = ("PLANE_VALUE", "PLANE_SHIFT")
        offsets = [equates[field] for field in (*fields, *stated)]
        assert offsets == sorted(offsets)
        assert max(offsets) < equates["PLANE_STATE_SIZE"]

    def test_every_plane_is_named_at_its_own_state_block(self, equates: Dict[str, int]) -> None:
        """The assembly holds a state block per plane, named and ordered as the song block is."""
        planes = [f"{name.upper()}_PLANE" for name in PlaneOrder.names()]
        expected = [plane * equates["PLANE_STATE_SIZE"] for plane in range(PLANE_COUNT)]
        assert [equates[plane] for plane in planes] == expected
