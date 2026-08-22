import ast
from pathlib import Path
from typing import Dict, Final

import pytest

from sampletones_player.compression.pitch import PITCH_COUNT
from sampletones_player.driver.assembler.layout import INCLUDE_DIRECTORY
from sampletones_player.specification.binary import WORD_SIZE
from sampletones_player.specification.compression import (
    OPCODE_SIZE,
    PHRASE_ID_ESCAPE,
    PHRASE_LENGTH_SIZE,
    PHRASE_TABLE_COUNT_SIZE,
    PHRASE_TABLE_ENTRY_SIZE,
    PLANE_COUNT,
    PLANE_STATE_SIZE,
    TOKEN_OPERAND_MASK,
    TOKEN_TAG_MASK,
    TokenTag,
)
from sampletones_player.specification.song import (
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

SONG_INCLUDE: Final[str] = "song.inc"
HEXADECIMAL_MARKER: Final[str] = "$"
HEXADECIMAL_PREFIX: Final[str] = "0x"
ASSIGNMENT: Final[str] = "="

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
    "PITCH_COUNT": PITCH_COUNT,
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
    "PLANE_STATE_SIZE": PLANE_STATE_SIZE,
    "PLANE_STATE_BYTES": PLANE_COUNT * PLANE_STATE_SIZE,
}


def _value(node: ast.expr, defined: Dict[str, int]) -> int:
    """The number an equate's expression comes to, over the equates before it."""
    match node:
        case ast.Constant(value=int() as number):
            return number
        case ast.Name(id=name):
            return defined[name]
        case ast.BinOp(left=left, op=ast.Add(), right=right):
            return _value(left, defined) + _value(right, defined)
        case ast.BinOp(left=left, op=ast.Mult(), right=right):
            return _value(left, defined) * _value(right, defined)

    raise ValueError(f"an equate reads {ast.dump(node)}, which the include holds no form for")


def read_equates(path: Path) -> Dict[str, int]:
    """Reads the constants an assembly include states, each over the ones stated before it.

    The driver and the exporter read one song block, so what the assembly believes about the
    layout is held against what the specification states. An include line is ``NAME = value``,
    where the value is a number, another equate, or the two joined by an addition or a product.

    Args:
        path: The include file to read.

    Returns:
        Dict[str, int]: The value each equate comes to.
    """
    defined: Dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ASSIGNMENT not in line:
            continue

        name, expression = line.split(ASSIGNMENT, 1)
        parsed = ast.parse(expression.strip().replace(HEXADECIMAL_MARKER, HEXADECIMAL_PREFIX), mode="eval")
        defined[name.strip()] = _value(parsed.body, defined)

    return defined


@pytest.fixture(name="equates", scope="module")
def equates_fixture() -> Dict[str, int]:
    return read_equates(INCLUDE_DIRECTORY / SONG_INCLUDE)


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
        planes = (
            "PULSE1_CONTROL_PLANE",
            "PULSE1_VALUE_PLANE",
            "PULSE2_CONTROL_PLANE",
            "PULSE2_VALUE_PLANE",
            "TRIANGLE_CONTROL_PLANE",
            "TRIANGLE_VALUE_PLANE",
            "NOISE_CONTROL_PLANE",
            "NOISE_VALUE_PLANE",
        )
        expected = [plane * equates["PLANE_STATE_SIZE"] for plane in range(PLANE_COUNT)]
        assert [equates[plane] for plane in planes] == expected
