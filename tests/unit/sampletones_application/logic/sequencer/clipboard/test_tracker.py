from dataclasses import dataclass
from typing import List, Optional

import pytest

from sampletones_application.logic.sequencer.clipboard.tracker import TrackerBlockText
from sampletones_application.logic.sequencer.tracker.block import TrackerBlock
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.note_off import NoteOff

SAMPLE_IDS: List[str] = ["kick", "snare", "hat"]


class FakeSampleDirectory:
    """A list of samples, standing where the project's own list would."""

    def __init__(self, sample_ids: List[str]) -> None:
        self._sample_ids = sample_ids

    def position_of(self, sample_id: str) -> Optional[int]:
        if sample_id not in self._sample_ids:
            return None

        return self._sample_ids.index(sample_id)

    def sample_at(self, position: int) -> Optional[str]:
        if 0 <= position < len(self._sample_ids):
            return self._sample_ids[position]

        return None


@pytest.fixture
def text() -> TrackerBlockText:
    return TrackerBlockText(samples=FakeSampleDirectory(SAMPLE_IDS))


def _slot(generator: Optional[GeneratorName], subcolumn: SubColumn) -> int:
    return TrackerSlot(generator, subcolumn).flat_index


def _region(
    *,
    first_slot: int,
    last_slot: int,
    rows: int = 1,
) -> TrackerRegion:
    return TrackerRegion(
        first_row=0,
        last_row=rows - 1,
        first_slot=first_slot,
        last_slot=last_slot,
    )


PULSE1_CELL = _region(
    first_slot=_slot(GeneratorName.PULSE1, SubColumn.INSTRUMENT),
    last_slot=_slot(GeneratorName.PULSE1, SubColumn.VOLUME),
)


def _body(text: TrackerBlockText, block: TrackerBlock, region: TrackerRegion) -> List[str]:
    return text.state(block, region).splitlines()[1:]


class TestTheFormAFieldTakes:
    """Every field carries what the grid shows in its cell, each kind in its own width."""

    def test_a_cell_of_values_prints_the_three_the_grid_prints(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={(0, 0): "snare"}, transposes={(0, 1): 0}, volumes={(0, 2): 15})

        assert _body(text, block, PULSE1_CELL) == ["01 +00 F"]

    def test_an_empty_cell_prints_the_dots_beneath_it(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={(0, 0): None}, transposes={(0, 1): None}, volumes={(0, 2): None})

        assert _body(text, block, PULSE1_CELL) == [".. ... ."]

    def test_a_mixed_cell_fills_its_fields_with_marks(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={}, transposes={}, volumes={})

        assert _body(text, block, PULSE1_CELL) == ["?? ??? ?"]

    def test_a_cut_prints_the_mark_the_note_column_shows(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={(0, 0): NoteOff()}, transposes={}, volumes={})

        assert _body(text, block, PULSE1_CELL) == ["~~ ??? ?"]

    def test_a_transpose_below_zero_prints_its_sign(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={}, transposes={(0, 1): -10}, volumes={})

        assert _body(text, block, PULSE1_CELL) == ["?? -0A ?"]

    def test_a_note_naming_a_sample_the_list_lacks_prints_as_mixed(self, text: TrackerBlockText) -> None:
        """A paste has nothing to place for it, so the text states nothing about that cell."""
        block = TrackerBlock(notes={(0, 0): "cowbell"}, transposes={}, volumes={})

        assert _body(text, block, PULSE1_CELL) == ["?? ??? ?"]


class TestTheShapeAStatementCovers:
    def test_a_header_opens_the_text_with_the_grid_and_the_slots(self, text: TrackerBlockText) -> None:
        region = _region(
            first_slot=_slot(GeneratorName.PULSE1, SubColumn.INSTRUMENT),
            last_slot=_slot(GeneratorName.PULSE2, SubColumn.VOLUME),
            rows=4,
        )

        header = text.state(TrackerBlock(notes={}, transposes={}, volumes={}), region).splitlines()[0]

        assert header == "SampleToNES/1 tracker rows=4 slots=3..8"

    def test_a_bar_stands_between_the_columns_a_row_crosses(self, text: TrackerBlockText) -> None:
        region = _region(
            first_slot=_slot(GeneratorName.PULSE1, SubColumn.INSTRUMENT),
            last_slot=_slot(GeneratorName.PULSE2, SubColumn.VOLUME),
        )

        assert _body(text, TrackerBlock(notes={}, transposes={}, volumes={}), region) == ["?? ??? ? | ?? ??? ?"]

    def test_a_row_of_the_block_prints_a_line_of_its_own(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={}, transposes={(0, 1): 1, (2, 1): 3}, volumes={})
        region = _region(
            first_slot=_slot(GeneratorName.PULSE1, SubColumn.INSTRUMENT),
            last_slot=_slot(GeneratorName.PULSE1, SubColumn.VOLUME),
            rows=3,
        )

        assert _body(text, block, region) == ["?? +01 ?", "?? ??? ?", "?? +03 ?"]


@dataclass(frozen=True)
class RoundTripCase:
    name: str
    block: TrackerBlock
    region: TrackerRegion


ROUND_TRIPS: List[RoundTripCase] = [
    RoundTripCase(
        "the three states across one cell",
        TrackerBlock(notes={(0, 0): "kick"}, transposes={(0, 1): None}, volumes={}),
        PULSE1_CELL,
    ),
    RoundTripCase(
        "a cut and an empty note",
        TrackerBlock(notes={(0, 0): NoteOff(), (1, 0): None}, transposes={}, volumes={}),
        _region(
            first_slot=_slot(GeneratorName.PULSE1, SubColumn.INSTRUMENT),
            last_slot=_slot(GeneratorName.PULSE1, SubColumn.VOLUME),
            rows=2,
        ),
    ),
    RoundTripCase(
        "the whole transpose range",
        TrackerBlock(notes={}, transposes={(0, 1): -24, (1, 1): 36, (2, 1): 0}, volumes={}),
        _region(
            first_slot=_slot(GeneratorName.PULSE1, SubColumn.INSTRUMENT),
            last_slot=_slot(GeneratorName.PULSE1, SubColumn.VOLUME),
            rows=3,
        ),
    ),
    RoundTripCase(
        "the whole volume range",
        TrackerBlock(notes={}, transposes={}, volumes={(0, 2): 0, (1, 2): 15}),
        _region(
            first_slot=_slot(GeneratorName.PULSE1, SubColumn.INSTRUMENT),
            last_slot=_slot(GeneratorName.PULSE1, SubColumn.VOLUME),
            rows=2,
        ),
    ),
    RoundTripCase(
        "a block anchored at the sample column",
        TrackerBlock(notes={(0, 0): "hat"}, transposes={(0, 4): 2}, volumes={(0, 5): 9}),
        _region(
            first_slot=_slot(None, SubColumn.INSTRUMENT),
            last_slot=_slot(GeneratorName.PULSE1, SubColumn.VOLUME),
        ),
    ),
    RoundTripCase(
        "a block starting and ending mid-cell",
        TrackerBlock(notes={(0, 3): "snare"}, transposes={(0, 1): 5, (0, 4): None}, volumes={(0, 2): 3}),
        _region(
            first_slot=_slot(GeneratorName.PULSE1, SubColumn.TRANSPOSE),
            last_slot=_slot(GeneratorName.PULSE2, SubColumn.TRANSPOSE),
        ),
    ),
    RoundTripCase(
        "the whole grid",
        TrackerBlock(notes={(0, 12): "kick"}, transposes={(1, 1): -1}, volumes={(1, 14): 4}),
        _region(
            first_slot=_slot(None, SubColumn.INSTRUMENT),
            last_slot=_slot(GeneratorName.NOISE, SubColumn.VOLUME),
            rows=2,
        ),
    ),
]


class TestRoundTrip:
    """A block stated as text and read back is the block it set out as."""

    @pytest.mark.parametrize("case", ROUND_TRIPS, ids=lambda case: case.name)
    def test_a_block_survives_being_stated_and_read(
        self,
        text: TrackerBlockText,
        case: RoundTripCase,
    ) -> None:
        assert text.parse(text.state(case.block, case.region)) == case.block

    def test_a_note_reaches_the_sample_standing_at_its_position(self, text: TrackerBlockText) -> None:
        """The position is what crosses, so a block lands on the list the reading project holds."""
        block = TrackerBlock(notes={(0, 0): "snare"}, transposes={}, volumes={})
        stated = text.state(block, PULSE1_CELL)

        elsewhere = TrackerBlockText(samples=FakeSampleDirectory(["bass", "clap"]))

        assert elsewhere.parse(stated) == TrackerBlock(notes={(0, 0): "clap"}, transposes={}, volumes={})

    def test_a_position_the_reading_list_falls_short_of_states_nothing(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={(0, 0): "hat"}, transposes={}, volumes={})
        stated = text.state(block, PULSE1_CELL)

        elsewhere = TrackerBlockText(samples=FakeSampleDirectory(["bass"]))

        assert elsewhere.parse(stated) == TrackerBlock(notes={}, transposes={}, volumes={})


class TestTextTypedByHand:
    """The form is readable, so a reader typing it reaches the same block a copy would."""

    def test_hexadecimal_reads_in_either_case(self, text: TrackerBlockText) -> None:
        upper = text.parse("SampleToNES/1 tracker rows=1 slots=3..5\n02 -0a f")
        lower = text.parse("SampleToNES/1 tracker rows=1 slots=3..5\n02 -0A F")

        assert upper == lower
        assert upper == TrackerBlock(notes={(0, 0): "hat"}, transposes={(0, 1): -10}, volumes={(0, 2): 15})

    def test_the_bars_between_columns_are_a_reading_aid(self, text: TrackerBlockText) -> None:
        with_bars = text.parse("SampleToNES/1 tracker rows=1 slots=3..8\n01 +00 F | .. ... .")
        without = text.parse("SampleToNES/1 tracker rows=1 slots=3..8\n01 +00 F .. ... .")

        assert with_bars is not None
        assert with_bars == without

    def test_a_trailing_line_break_leaves_the_block_as_it_stands(self, text: TrackerBlockText) -> None:
        assert text.parse("SampleToNES/1 tracker rows=1 slots=3..5\n01 +00 F\n") is not None


@dataclass(frozen=True)
class RefusalCase:
    name: str
    text: str


HEADER = "SampleToNES/1 tracker rows=2 slots=3..5"

REFUSALS: List[RefusalCase] = [
    RefusalCase("nothing at all", ""),
    RefusalCase("unrelated text", "check out this riff\nit goes hard"),
    RefusalCase("a header alone", HEADER),
    RefusalCase("a truncated body", f"{HEADER}\n01 +00 F"),
    RefusalCase("a body reaching past the header", f"{HEADER}\n01 +00 F\n01 +00 F\n01 +00 F"),
    RefusalCase("a line short of a field", f"{HEADER}\n01 +00\n01 +00 F"),
    RefusalCase("a line with a field too many", f"{HEADER}\n01 +00 F 2\n01 +00 F"),
    RefusalCase("an order's block", "SampleToNES/1 order rows=1 positions=0..1\n01 02"),
    RefusalCase("a slot past the grid", "SampleToNES/1 tracker rows=1 slots=13..15\n01 +00 F"),
    RefusalCase("a word in a note field", f"{HEADER}\nxx +00 F\n01 +00 F"),
    RefusalCase("an unsigned transpose", f"{HEADER}\n01 12 F\n01 +00 F"),
    RefusalCase("a transpose past the range", f"{HEADER}\n01 +40 F\n01 +00 F"),
    RefusalCase("a transpose below the range", f"{HEADER}\n01 -40 F\n01 +00 F"),
    RefusalCase("a volume past the range", f"{HEADER}\n01 +00 FF\n01 +00 F"),
    RefusalCase("dots and marks in one field", f"{HEADER}\n.? +00 F\n01 +00 F"),
]


class TestRefusals:
    """Text this grid never wrote states no block, so the slot the tracker copied into stands."""

    @pytest.mark.parametrize("case", REFUSALS, ids=lambda case: case.name)
    def test_text_outside_the_form_states_no_block(
        self,
        text: TrackerBlockText,
        case: RefusalCase,
    ) -> None:
        assert text.parse(case.text) is None
