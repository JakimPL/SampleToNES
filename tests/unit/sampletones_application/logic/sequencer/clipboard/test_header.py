from dataclasses import dataclass
from typing import List, Optional

import pytest

from sampletones_application.logic.sequencer.clipboard.header import (
    BLOCK_MAGIC,
    BlockShape,
    parse_header,
    state_header,
)

GRID = "tracker"
SPAN_KEY = "slots"


def _parse(line: str) -> Optional[BlockShape]:
    return parse_header(line, grid=GRID, span_key=SPAN_KEY)


class TestStating:
    def test_a_header_names_the_grid_and_the_shape(self) -> None:
        shape = BlockShape(rows=4, first=3, last=11)

        line = state_header(grid=GRID, span_key=SPAN_KEY, shape=shape)

        assert line == f"{BLOCK_MAGIC} tracker rows=4 slots=3..11"

    def test_a_span_of_one_slot_names_the_same_bound_twice(self) -> None:
        shape = BlockShape(rows=1, first=7, last=7)

        line = state_header(grid=GRID, span_key=SPAN_KEY, shape=shape)

        assert line == f"{BLOCK_MAGIC} tracker rows=1 slots=7..7"


class TestParsing:
    def test_a_stated_header_reads_back_as_the_shape_it_named(self) -> None:
        shape = BlockShape(rows=4, first=3, last=11)

        assert _parse(state_header(grid=GRID, span_key=SPAN_KEY, shape=shape)) == shape

    def test_the_width_counts_both_bounds(self) -> None:
        assert BlockShape(rows=1, first=3, last=11).width == 9

    def test_surrounding_spaces_leave_the_shape_as_it_stands(self) -> None:
        assert _parse(f"  {BLOCK_MAGIC}   tracker  rows=2   slots=0..2  ") == BlockShape(rows=2, first=0, last=2)


@dataclass(frozen=True)
class RefusalCase:
    name: str
    line: str


REFUSALS: List[RefusalCase] = [
    RefusalCase("another application", "Tracker/1 tracker rows=2 slots=0..2"),
    RefusalCase("another grid", f"{BLOCK_MAGIC} order rows=2 slots=0..2"),
    RefusalCase("another span", f"{BLOCK_MAGIC} tracker rows=2 positions=0..2"),
    RefusalCase("a missing span", f"{BLOCK_MAGIC} tracker rows=2"),
    RefusalCase("a trailing word", f"{BLOCK_MAGIC} tracker rows=2 slots=0..2 more"),
    RefusalCase("no rows at all", f"{BLOCK_MAGIC} tracker rows=0 slots=0..2"),
    RefusalCase("a fractional count", f"{BLOCK_MAGIC} tracker rows=2.5 slots=0..2"),
    RefusalCase("a negative count", f"{BLOCK_MAGIC} tracker rows=-2 slots=0..2"),
    RefusalCase("bounds out of order", f"{BLOCK_MAGIC} tracker rows=2 slots=11..3"),
    RefusalCase("one bound", f"{BLOCK_MAGIC} tracker rows=2 slots=3"),
    RefusalCase("a wordy bound", f"{BLOCK_MAGIC} tracker rows=2 slots=three..11"),
    RefusalCase("a label with no value", f"{BLOCK_MAGIC} tracker rows slots=3..11"),
    RefusalCase("a line of prose", "have a look at this pattern"),
    RefusalCase("nothing at all", ""),
]


class TestRefusals:
    """A header states this grid's form, and anything else states no shape at all."""

    @pytest.mark.parametrize("case", REFUSALS, ids=lambda case: case.name)
    def test_a_header_this_grid_never_wrote_states_no_shape(self, case: RefusalCase) -> None:
        assert _parse(case.line) is None
