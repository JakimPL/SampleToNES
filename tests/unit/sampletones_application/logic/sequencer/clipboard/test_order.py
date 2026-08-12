from dataclasses import dataclass
from typing import List

import pytest

from sampletones_application.logic.sequencer.clipboard.order import OrderBlockText
from sampletones_application.logic.sequencer.order.block import OrderBlock
from sampletones_application.view_model.sequencer.region import OrderRegion


@pytest.fixture
def text() -> OrderBlockText:
    return OrderBlockText()


def _region(
    *,
    rows: int = 1,
    first_position: int = 0,
    positions: int = 1,
    first_row: int = 0,
) -> OrderRegion:
    return OrderRegion(
        first_row=first_row,
        last_row=first_row + rows - 1,
        first_position=first_position,
        last_position=first_position + positions - 1,
    )


def _body(text: OrderBlockText, block: OrderBlock, region: OrderRegion) -> List[str]:
    return text.state(block, region).splitlines()[1:]


class TestTheFormAFieldTakes:
    """Every field carries what the table shows in its cell."""

    def test_a_pattern_prints_the_index_the_table_shows(self, text: OrderBlockText) -> None:
        block = OrderBlock(entries={(0, 0): 1, (0, 1): 26})

        assert _body(text, block, _region(positions=2)) == ["01 1A"]

    def test_a_silent_slot_prints_the_dots_beneath_it(self, text: OrderBlockText) -> None:
        assert _body(text, OrderBlock(entries={(0, 0): None}), _region()) == [".."]

    def test_a_mixed_cell_fills_its_field_with_marks(self, text: OrderBlockText) -> None:
        assert _body(text, OrderBlock(entries={}), _region()) == ["??"]

    def test_a_row_of_the_block_prints_a_line_of_its_own(self, text: OrderBlockText) -> None:
        block = OrderBlock(entries={(0, 0): 0, (1, 0): 1, (2, 0): None})

        assert _body(text, block, _region(rows=3)) == ["00", "01", ".."]


class TestTheShapeAStatementCovers:
    def test_a_header_opens_the_text_with_the_grid_and_the_positions(self, text: OrderBlockText) -> None:
        region = _region(rows=3, first_position=5, positions=4)

        header = text.state(OrderBlock(entries={}), region).splitlines()[0]

        assert header == "SampleToNES/1 order rows=3 positions=5..8"


@dataclass(frozen=True)
class RoundTripCase:
    name: str
    block: OrderBlock
    region: OrderRegion


ROUND_TRIPS: List[RoundTripCase] = [
    RoundTripCase(
        "the three states across one row",
        OrderBlock(entries={(0, 0): 3, (0, 1): None}),
        _region(positions=3),
    ),
    RoundTripCase(
        "a block starting past the first frame",
        OrderBlock(entries={(0, 0): 1, (0, 1): 2}),
        _region(first_position=7, positions=2),
    ),
    RoundTripCase(
        "every channel row",
        OrderBlock(entries={(0, 0): 1, (1, 0): 1, (2, 0): 2, (3, 0): None, (4, 0): 0}),
        _region(rows=5, positions=1),
    ),
    RoundTripCase(
        "the master row over channels that disagree",
        OrderBlock(entries={(1, 0): 1, (1, 1): 2, (2, 0): 1}),
        _region(rows=3, positions=2),
    ),
    RoundTripCase(
        "an index past a single digit",
        OrderBlock(entries={(0, 0): 255}),
        _region(),
    ),
]


class TestRoundTrip:
    """A block stated as text and read back is the block it set out as."""

    @pytest.mark.parametrize("case", ROUND_TRIPS, ids=lambda case: case.name)
    def test_a_block_survives_being_stated_and_read(
        self,
        text: OrderBlockText,
        case: RoundTripCase,
    ) -> None:
        assert text.parse(text.state(case.block, case.region)) == case.block

    def test_a_master_row_the_channels_disagree_over_states_nothing(self, text: OrderBlockText) -> None:
        """Its marks reach the reading as an absent key, so a paste passes that cell by."""
        stated = text.state(OrderBlock(entries={(0, 1): 4}), _region(positions=2))

        assert text.parse(stated) == OrderBlock(entries={(0, 1): 4})


class TestTextTypedByHand:
    def test_hexadecimal_reads_in_either_case(self, text: OrderBlockText) -> None:
        upper = text.parse("SampleToNES/1 order rows=1 positions=0..1\n0a 1f")
        lower = text.parse("SampleToNES/1 order rows=1 positions=0..1\n0A 1F")

        assert upper == lower
        assert upper == OrderBlock(entries={(0, 0): 10, (0, 1): 31})

    def test_a_trailing_line_break_leaves_the_block_as_it_stands(self, text: OrderBlockText) -> None:
        assert text.parse("SampleToNES/1 order rows=1 positions=0..0\n01\n") is not None


@dataclass(frozen=True)
class RefusalCase:
    name: str
    text: str


HEADER = "SampleToNES/1 order rows=2 positions=0..1"

REFUSALS: List[RefusalCase] = [
    RefusalCase("nothing at all", ""),
    RefusalCase("unrelated text", "the order goes\nintro then verse"),
    RefusalCase("a header alone", HEADER),
    RefusalCase("a truncated body", f"{HEADER}\n01 02"),
    RefusalCase("a body reaching past the header", f"{HEADER}\n01 02\n01 02\n01 02"),
    RefusalCase("a line short of a field", f"{HEADER}\n01\n01 02"),
    RefusalCase("a line with a field too many", f"{HEADER}\n01 02 03\n01 02"),
    RefusalCase("a tracker's block", "SampleToNES/1 tracker rows=1 slots=3..5\n01 +00 F"),
    RefusalCase("more rows than the table has", "SampleToNES/1 order rows=6 positions=0..0\n01\n01\n01\n01\n01\n01"),
    RefusalCase("a word in a field", f"{HEADER}\nxx 02\n01 02"),
    RefusalCase("a signed index", f"{HEADER}\n+1 02\n01 02"),
    RefusalCase("dots and marks in one field", f"{HEADER}\n.? 02\n01 02"),
]


class TestRefusals:
    """Text this table never wrote states no block, so the slot the order copied into stands."""

    @pytest.mark.parametrize("case", REFUSALS, ids=lambda case: case.name)
    def test_text_outside_the_form_states_no_block(
        self,
        text: OrderBlockText,
        case: RefusalCase,
    ) -> None:
        assert text.parse(case.text) is None
