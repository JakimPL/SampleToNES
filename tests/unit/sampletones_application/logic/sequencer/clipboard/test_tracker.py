from dataclasses import dataclass
from typing import List, Optional

import pytest

from sampletones_application.logic.sequencer.clipboard.tracker import TrackerBlockText
from sampletones_application.logic.sequencer.tracker.block import TrackerBlock
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD, MAX_PITCH, MAX_TRANSPOSE, MIN_PLAYED_PITCH, MIN_TRANSPOSE
from sampletones_core.project.patterns.pitch import Note, Step
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.utils.frequencies import period_to_name, pitch_to_name

SAMPLE_IDS: List[str] = ["kick", "snare", "hat"]


class FakeSampleDirectory:
    """A list of samples, standing where the project's own list would."""

    def __init__(self, voice_ids: List[str]) -> None:
        self._voice_ids = voice_ids

    def position_of(self, voice_id: str) -> Optional[int]:
        if voice_id not in self._voice_ids:
            return None

        return self._voice_ids.index(voice_id)

    def sample_at(self, position: int) -> Optional[str]:
        if 0 <= position < len(self._voice_ids):
            return self._voice_ids[position]

        return None


@pytest.fixture
def text() -> TrackerBlockText:
    return TrackerBlockText(samples=FakeSampleDirectory(SAMPLE_IDS))


def _slot(channel: Optional[ChannelName], subcolumn: SubColumn) -> int:
    return TrackerSlot(channel, subcolumn).flat_index


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
    first_slot=_slot(ChannelName.PULSE1, SubColumn.VOICE),
    last_slot=_slot(ChannelName.PULSE1, SubColumn.VOLUME),
)


def _body(text: TrackerBlockText, block: TrackerBlock, region: TrackerRegion) -> List[str]:
    return text.state(block, region).splitlines()[1:]


class TestTheFormAFieldTakes:
    """Every field carries what the grid shows in its cell, each kind in its own width."""

    def test_a_cell_of_values_prints_the_three_the_grid_prints(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={(0, 0): "snare"}, pitches={(0, 1): Step(value=0)}, volumes={(0, 2): 15})

        assert _body(text, block, PULSE1_CELL) == ["01 +00 F"]

    def test_an_empty_cell_prints_the_dots_beneath_it(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={(0, 0): None}, pitches={(0, 1): None}, volumes={(0, 2): None})

        assert _body(text, block, PULSE1_CELL) == [".. ... ."]

    def test_a_mixed_cell_fills_its_fields_with_marks(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={}, pitches={}, volumes={})

        assert _body(text, block, PULSE1_CELL) == ["?? ??? ?"]

    def test_a_cut_prints_the_mark_the_note_column_shows(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={(0, 0): NoteOff()}, pitches={}, volumes={})

        assert _body(text, block, PULSE1_CELL) == ["~~ ??? ?"]

    def test_a_step_below_zero_prints_its_sign_in_decimal(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={}, pitches={(0, 1): Step(value=-10)}, volumes={})

        assert _body(text, block, PULSE1_CELL) == ["?? -10 ?"]

    def test_a_note_prints_its_name(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={}, pitches={(0, 1): Note(value=61)}, volumes={})

        assert _body(text, block, PULSE1_CELL) == [f"?? {pitch_to_name(61)} ?"]

    def test_a_period_prints_its_name(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={}, pitches={(0, 1): Note(value=5)}, volumes={})

        assert _body(text, block, PULSE1_CELL) == [f"?? {period_to_name(5)} ?"]

    def test_a_note_naming_a_sample_the_list_lacks_prints_as_mixed(self, text: TrackerBlockText) -> None:
        """A paste has nothing to place for it, so the text states nothing about that cell."""
        block = TrackerBlock(notes={(0, 0): "cowbell"}, pitches={}, volumes={})

        assert _body(text, block, PULSE1_CELL) == ["?? ??? ?"]


class TestTheShapeAStatementCovers:
    def test_a_header_opens_the_text_with_the_grid_and_the_slots(self, text: TrackerBlockText) -> None:
        region = _region(
            first_slot=_slot(ChannelName.PULSE1, SubColumn.VOICE),
            last_slot=_slot(ChannelName.PULSE2, SubColumn.VOLUME),
            rows=4,
        )

        header = text.state(TrackerBlock(notes={}, pitches={}, volumes={}), region).splitlines()[0]

        assert header == "SampleToNES/1 tracker rows=4 slots=3..8"

    def test_a_bar_stands_between_the_columns_a_row_crosses(self, text: TrackerBlockText) -> None:
        region = _region(
            first_slot=_slot(ChannelName.PULSE1, SubColumn.VOICE),
            last_slot=_slot(ChannelName.PULSE2, SubColumn.VOLUME),
        )

        assert _body(text, TrackerBlock(notes={}, pitches={}, volumes={}), region) == ["?? ??? ? | ?? ??? ?"]

    def test_a_row_of_the_block_prints_a_line_of_its_own(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={}, pitches={(0, 1): Step(value=1), (2, 1): Step(value=3)}, volumes={})
        region = _region(
            first_slot=_slot(ChannelName.PULSE1, SubColumn.VOICE),
            last_slot=_slot(ChannelName.PULSE1, SubColumn.VOLUME),
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
        TrackerBlock(notes={(0, 0): "kick"}, pitches={(0, 1): None}, volumes={}),
        PULSE1_CELL,
    ),
    RoundTripCase(
        "a cut and an empty note",
        TrackerBlock(notes={(0, 0): NoteOff(), (1, 0): None}, pitches={}, volumes={}),
        _region(
            first_slot=_slot(ChannelName.PULSE1, SubColumn.VOICE),
            last_slot=_slot(ChannelName.PULSE1, SubColumn.VOLUME),
            rows=2,
        ),
    ),
    RoundTripCase(
        "the whole step range",
        TrackerBlock(
            notes={},
            pitches={(0, 1): Step(value=MIN_TRANSPOSE), (1, 1): Step(value=MAX_TRANSPOSE), (2, 1): Step(value=0)},
            volumes={},
        ),
        _region(
            first_slot=_slot(ChannelName.PULSE1, SubColumn.VOICE),
            last_slot=_slot(ChannelName.PULSE1, SubColumn.VOLUME),
            rows=3,
        ),
    ),
    RoundTripCase(
        "the whole note range",
        TrackerBlock(
            notes={},
            pitches={(0, 1): Note(value=MIN_PLAYED_PITCH), (1, 1): Note(value=60), (2, 1): Note(value=MAX_PITCH)},
            volumes={},
        ),
        _region(
            first_slot=_slot(ChannelName.PULSE1, SubColumn.VOICE),
            last_slot=_slot(ChannelName.PULSE1, SubColumn.VOLUME),
            rows=3,
        ),
    ),
    RoundTripCase(
        "the whole period range",
        TrackerBlock(notes={}, pitches={(0, 1): Note(value=0), (1, 1): Note(value=MAX_PERIOD)}, volumes={}),
        _region(
            first_slot=_slot(ChannelName.NOISE, SubColumn.VOICE),
            last_slot=_slot(ChannelName.NOISE, SubColumn.VOLUME),
            rows=2,
        ),
    ),
    RoundTripCase(
        "both faces down one column",
        TrackerBlock(notes={}, pitches={(0, 1): Note(value=60), (1, 1): Step(value=-3)}, volumes={}),
        _region(
            first_slot=_slot(ChannelName.PULSE1, SubColumn.VOICE),
            last_slot=_slot(ChannelName.PULSE1, SubColumn.VOLUME),
            rows=2,
        ),
    ),
    RoundTripCase(
        "a note in the sample column",
        TrackerBlock(notes={}, pitches={(0, 1): Note(value=60)}, volumes={}),
        _region(
            first_slot=_slot(None, SubColumn.VOICE),
            last_slot=_slot(None, SubColumn.VOLUME),
        ),
    ),
    RoundTripCase(
        "the whole volume range",
        TrackerBlock(notes={}, pitches={}, volumes={(0, 2): 0, (1, 2): 15}),
        _region(
            first_slot=_slot(ChannelName.PULSE1, SubColumn.VOICE),
            last_slot=_slot(ChannelName.PULSE1, SubColumn.VOLUME),
            rows=2,
        ),
    ),
    RoundTripCase(
        "a block anchored at the sample column",
        TrackerBlock(notes={(0, 0): "hat"}, pitches={(0, 4): Step(value=2)}, volumes={(0, 5): 9}),
        _region(
            first_slot=_slot(None, SubColumn.VOICE),
            last_slot=_slot(ChannelName.PULSE1, SubColumn.VOLUME),
        ),
    ),
    RoundTripCase(
        "a block starting and ending mid-cell",
        TrackerBlock(notes={(0, 3): "snare"}, pitches={(0, 1): Step(value=5), (0, 4): None}, volumes={(0, 2): 3}),
        _region(
            first_slot=_slot(ChannelName.PULSE1, SubColumn.TRANSPOSE),
            last_slot=_slot(ChannelName.PULSE2, SubColumn.TRANSPOSE),
        ),
    ),
    RoundTripCase(
        "the whole grid",
        TrackerBlock(notes={(0, 12): "kick"}, pitches={(1, 1): Step(value=-1)}, volumes={(1, 14): 4}),
        _region(
            first_slot=_slot(None, SubColumn.VOICE),
            last_slot=_slot(ChannelName.NOISE, SubColumn.VOLUME),
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
        block = TrackerBlock(notes={(0, 0): "snare"}, pitches={}, volumes={})
        stated = text.state(block, PULSE1_CELL)

        elsewhere = TrackerBlockText(samples=FakeSampleDirectory(["bass", "clap"]))

        assert elsewhere.parse(stated) == TrackerBlock(notes={(0, 0): "clap"}, pitches={}, volumes={})

    def test_a_position_the_reading_list_falls_short_of_states_nothing(self, text: TrackerBlockText) -> None:
        block = TrackerBlock(notes={(0, 0): "hat"}, pitches={}, volumes={})
        stated = text.state(block, PULSE1_CELL)

        elsewhere = TrackerBlockText(samples=FakeSampleDirectory(["bass"]))

        assert elsewhere.parse(stated) == TrackerBlock(notes={}, pitches={}, volumes={})


class TestTextTypedByHand:
    """The form is readable, so a reader typing it reaches the same block a copy would."""

    def test_hexadecimal_reads_in_either_case(self, text: TrackerBlockText) -> None:
        upper = text.parse("SampleToNES/1 tracker rows=1 slots=3..5\n02 -10 f")
        lower = text.parse("SampleToNES/1 tracker rows=1 slots=3..5\n02 -10 F")

        assert upper == lower
        assert upper == TrackerBlock(notes={(0, 0): "hat"}, pitches={(0, 1): Step(value=-10)}, volumes={(0, 2): 15})

    @pytest.mark.parametrize(
        ("field", "expected"),
        [
            ("c#3", Note(value=61)),
            ("C-0", Note(value=MIN_PLAYED_PITCH)),
            ("B-7", Note(value=MAX_PITCH)),
            ("a-#", Note(value=10)),
            ("+7", Step(value=7)),
            ("-07", Step(value=-7)),
        ],
    )
    def test_a_pitch_typed_by_hand_reads_as_the_grid_prints_it(
        self,
        text: TrackerBlockText,
        field: str,
        expected: object,
    ) -> None:
        block = text.parse(f"SampleToNES/1 tracker rows=1 slots=4..4\n{field}")

        assert block == TrackerBlock(notes={}, pitches={(0, 1): expected}, volumes={})

    @pytest.mark.parametrize("field", ["C-8", "H-3", "G-#", "12", "+87", "-87", "+0A"])
    def test_a_pitch_the_form_has_no_reading_for_refuses_the_text(self, text: TrackerBlockText, field: str) -> None:
        assert text.parse(f"SampleToNES/1 tracker rows=1 slots=4..4\n{field}") is None

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
    RefusalCase("a step past the range", f"{HEADER}\n01 +{MAX_TRANSPOSE + 1:02d} F\n01 +00 F"),
    RefusalCase("a step below the range", f"{HEADER}\n01 -{abs(MIN_TRANSPOSE) + 1:02d} F\n01 +00 F"),
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
