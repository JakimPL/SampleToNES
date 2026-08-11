from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.tracker import (
    SequencerTrackerLogic,
    TrackerBlockReader,
    TrackerBlockWriter,
)
from sampletones_application.view_model.sequencer.region import TrackerCell, TrackerRegion
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.sequencer import (
    fill_frame,
    parse_block,
    render_frame,
    render_slots,
    sample_reconstruction,
)

FRAME_ROWS: Final[int] = 4
EMPTY: Final[str] = ".. ... . | .. ... . | .. ... . | .. ... ."
LEAD: Final[str] = "00"
BASS: Final[str] = "01"


@dataclass(frozen=True, kw_only=True)
class Grid:
    """A four-row frame with two samples, the state every paste case starts from."""

    controller: ProjectController
    logic: SequencerTrackerLogic
    writer: TrackerBlockWriter
    sample_ids: Tuple[str, ...]


@pytest.fixture
def grid() -> Grid:
    """A frame short enough for a case to state whole, holding a sample over two channels and one
    over a third.

    Which channels a sample governs is what the sample column fans a write out over, so the pair
    covers both readings: a write that reaches some channels and clears the rest, and a note
    written into a channel its own reconstruction leaves out.
    """
    controller = ProjectController(ProjectManager())
    logic = SequencerTrackerLogic(controller)
    logic.set_rows_per_pattern(FRAME_ROWS)
    lead = controller.add_sample(
        sample_reconstruction([GeneratorName.PULSE1, GeneratorName.PULSE2]),
        name="lead",
    )
    bass = controller.add_sample(
        sample_reconstruction([GeneratorName.TRIANGLE]),
        name="bass",
    )
    return Grid(
        controller=controller,
        logic=logic,
        writer=TrackerBlockWriter(logic),
        sample_ids=(lead.id, bass.id),
    )


class TestPaste(BaseTestSuite):
    """What a block writes where it lands, stated as the whole frame it leaves behind.

    A block carries the subcolumn offsets it was read at while the cell it is written from supplies
    only a row and a column, so every case states its origin as that pair: which subcolumn the
    cursor happened to stand in cannot reach the result.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        block: Tuple[str, ...]
        first_subcolumn: SubColumn
        origin: TrackerCell
        expected: Tuple[str, ...]
        frame: Tuple[str, ...] = ()

    test_cases = (
        TestCase(
            label="a block keeps its own kinds wherever the cursor stands",
            block=("+02 8",),
            first_subcolumn=SubColumn.TRANSPOSE,
            origin=TrackerCell(row=1, generator=GeneratorName.PULSE2),
            expected=(
                EMPTY,
                ".. ... . | .. +02 8 | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a sample through the sample column reaches its channels and clears the rest",
            frame=(".. ... . | .. ... . | .. ... . | .. ... 5",),
            block=(LEAD,),
            first_subcolumn=SubColumn.INSTRUMENT,
            origin=TrackerCell(row=0, generator=None),
            expected=(
                "00 ... . | 00 ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a channel beside the sample column overwrites what it settled",
            block=(f"{LEAD} ... . | {BASS}",),
            first_subcolumn=SubColumn.INSTRUMENT,
            origin=TrackerCell(row=0, generator=None),
            expected=(
                "01 ... . | 00 ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a block read from the sample column writes one channel when written to one",
            block=(LEAD,),
            first_subcolumn=SubColumn.INSTRUMENT,
            origin=TrackerCell(row=0, generator=GeneratorName.TRIANGLE),
            expected=(
                ".. ... . | .. ... . | 00 ... . | .. ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a mixed cell leaves its target as it stands while its neighbours clear theirs",
            frame=("00 +03 7 | .. ... . | .. ... . | .. ... .",),
            block=(".. ? .",),
            first_subcolumn=SubColumn.INSTRUMENT,
            origin=TrackerCell(row=0, generator=GeneratorName.PULSE1),
            expected=(
                ".. +03 . | .. ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="an explicit zero transpose lands while an empty one clears",
            frame=(".. +03 . | .. +05 . | .. ... . | .. ... .",),
            block=("+00 ? | ? ...",),
            first_subcolumn=SubColumn.TRANSPOSE,
            origin=TrackerCell(row=0, generator=GeneratorName.PULSE1),
            expected=(
                ".. +00 . | .. ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a cut through the sample column cuts every channel",
            frame=("00 ... . | 00 ... . | .. ... . | .. ... .",),
            block=("~~",),
            first_subcolumn=SubColumn.INSTRUMENT,
            origin=TrackerCell(row=0, generator=None),
            expected=(
                "~~ ... . | ~~ ... . | ~~ ... . | ~~ ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a note naming an absent sample writes nothing into a channel",
            frame=("00 +02 5 | .. ... . | .. ... . | .. ... .",),
            block=("!! ? ?",),
            first_subcolumn=SubColumn.INSTRUMENT,
            origin=TrackerCell(row=0, generator=GeneratorName.PULSE1),
            expected=(
                "00 +02 5 | .. ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a note naming an absent sample clears nothing through the sample column",
            frame=("00 ... . | 00 ... . | .. ... . | .. ... 5",),
            block=("!!",),
            first_subcolumn=SubColumn.INSTRUMENT,
            origin=TrackerCell(row=0, generator=None),
            expected=(
                "00 ... . | 00 ... . | .. ... . | .. ... 5",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="an empty instrument through the sample column clears every channel",
            frame=("00 ... . | 00 ... . | .. ... . | ~~ ... .",),
            block=("..",),
            first_subcolumn=SubColumn.INSTRUMENT,
            origin=TrackerCell(row=0, generator=None),
            expected=(EMPTY, EMPTY, EMPTY, EMPTY),
        ),
        TestCase(
            label="an empty transpose through an ungoverned sample column clears every channel",
            frame=(".. +02 . | .. +02 . | .. +02 . | .. +02 .",),
            block=("...",),
            first_subcolumn=SubColumn.TRANSPOSE,
            origin=TrackerCell(row=0, generator=None),
            expected=(EMPTY, EMPTY, EMPTY, EMPTY),
        ),
        TestCase(
            label="a transpose through a governed sample column reaches its channels alone",
            frame=("00 ... . | 00 ... . | .. ... . | .. ... .",),
            block=("+02",),
            first_subcolumn=SubColumn.TRANSPOSE,
            origin=TrackerCell(row=0, generator=None),
            expected=(
                "00 +02 . | 00 +02 . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a silent volume writes zero rather than emptiness",
            block=("0",),
            first_subcolumn=SubColumn.VOLUME,
            origin=TrackerCell(row=0, generator=GeneratorName.PULSE1),
            expected=(
                ".. ... 0 | .. ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="rows past the frame's last are dropped rather than wrapped",
            block=("+01", "+02", "+03"),
            first_subcolumn=SubColumn.TRANSPOSE,
            origin=TrackerCell(row=2, generator=GeneratorName.PULSE1),
            expected=(
                EMPTY,
                EMPTY,
                ".. +01 . | .. ... . | .. ... . | .. ... .",
                ".. +02 . | .. ... . | .. ... . | .. ... .",
            ),
        ),
        TestCase(
            label="slots past the last column are dropped rather than wrapped",
            block=(f"{LEAD} ... . | {BASS}",),
            first_subcolumn=SubColumn.INSTRUMENT,
            origin=TrackerCell(row=0, generator=GeneratorName.NOISE),
            expected=(
                ".. ... . | .. ... . | .. ... . | 00 ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a wholly mixed block leaves the frame as it stands",
            frame=("00 +02 5 | .. ... . | .. ... . | .. ... .",),
            block=("? ? ?",),
            first_subcolumn=SubColumn.INSTRUMENT,
            origin=TrackerCell(row=0, generator=GeneratorName.PULSE1),
            expected=(
                "00 +02 5 | .. ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a wholly empty block empties what it covers",
            frame=("00 +02 5 | 00 +02 5 | .. ... . | .. ... .",),
            block=(".. ... .",),
            first_subcolumn=SubColumn.INSTRUMENT,
            origin=TrackerCell(row=0, generator=GeneratorName.PULSE1),
            expected=(
                ".. ... . | 00 +02 5 | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
                EMPTY,
            ),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_frame_after_a_paste(
        self,
        grid: Grid,
        test_case: TestCase,
    ) -> None:
        fill_frame(grid.logic, test_case.frame, sample_ids=grid.sample_ids)
        block = parse_block(
            test_case.block,
            first_subcolumn=test_case.first_subcolumn,
            sample_ids=grid.sample_ids,
        )

        grid.writer.write(block, test_case.origin)

        assert render_frame(grid.logic) == test_case.expected


class TestSingleSlotEquivalence:
    """A block of one cell writes what typing that cell writes, which is what makes a paste
    explainable as the edits it is made of."""

    def test_a_single_cell_block_matches_the_edit_it_stands_for(self, grid: Grid) -> None:
        block = parse_block(
            ("+02",),
            first_subcolumn=SubColumn.TRANSPOSE,
            sample_ids=grid.sample_ids,
        )
        grid.writer.write(block, TrackerCell(row=0, generator=GeneratorName.PULSE1))
        pasted = render_frame(grid.logic)

        typed = _typed_grid()
        typed.set_cell_subcolumn(0, GeneratorName.PULSE1, transpose=2)

        assert pasted == render_frame(typed)


class TestClear:
    """What a delete empties, which is every subcolumn its region covers and nothing beside."""

    def test_a_region_empties_the_subcolumns_it_covers(self, grid: Grid) -> None:
        fill_frame(
            grid.logic,
            ("00 +02 5 | 00 +03 6 | .. ... . | .. ... .",),
            sample_ids=grid.sample_ids,
        )

        grid.writer.clear(
            TrackerRegion(
                first_row=0,
                last_row=0,
                first_slot=TrackerSlot(GeneratorName.PULSE1, SubColumn.TRANSPOSE).flat_index,
                last_slot=TrackerSlot(GeneratorName.PULSE2, SubColumn.INSTRUMENT).flat_index,
            )
        )

        assert render_frame(grid.logic)[0] == "00 ... . | .. +03 6 | .. ... . | .. ... ."

    def test_a_region_over_the_sample_column_empties_the_channels_it_governs(self, grid: Grid) -> None:
        fill_frame(
            grid.logic,
            ("00 +02 5 | 00 +02 5 | .. ... . | .. ... 5",),
            sample_ids=grid.sample_ids,
        )

        grid.writer.clear(
            TrackerRegion(
                first_row=0,
                last_row=0,
                first_slot=TrackerSlot(None, SubColumn.VOLUME).flat_index,
                last_slot=TrackerSlot(None, SubColumn.VOLUME).flat_index,
            )
        )

        assert render_frame(grid.logic)[0] == "00 +02 . | 00 +02 . | .. ... . | .. ... 5"


class TestRoundTrip:
    """Reading a region, emptying it and writing the block back leaves the frame it came from."""

    def test_a_block_written_back_at_its_origin_restores_the_frame(self, grid: Grid) -> None:
        fill_frame(
            grid.logic,
            (
                "00 +02 5 | 00 ... . | .. ... . | ~~ ... 3",
                ".. ... . | 01 +00 0 | .. +07 . | .. ... .",
            ),
            sample_ids=grid.sample_ids,
        )
        before = render_frame(grid.logic)
        region = TrackerRegion(
            first_row=0,
            last_row=1,
            first_slot=TrackerSlot(GeneratorName.PULSE1, SubColumn.INSTRUMENT).flat_index,
            last_slot=TrackerSlot(GeneratorName.NOISE, SubColumn.VOLUME).flat_index,
        )
        block = TrackerBlockReader(grid.logic).read(region)

        grid.writer.clear(region)
        grid.writer.write(block, TrackerCell(row=0, generator=GeneratorName.PULSE1))

        assert render_frame(grid.logic) == before


class TestMaterialisation:
    """A paste reaches a channel holding no pattern by giving it one, the way an edit does."""

    def test_a_frame_holding_no_pattern_gains_one_where_a_block_lands(self, grid: Grid) -> None:
        position = grid.controller.project.song.order_length()
        grid.controller.append_frame()
        grid.logic.select_frame(position)
        assert render_slots(grid.controller, position) == ".. .. .. .."

        block = parse_block(
            ("+02",),
            first_subcolumn=SubColumn.TRANSPOSE,
            sample_ids=grid.sample_ids,
        )
        grid.writer.write(block, TrackerCell(row=0, generator=GeneratorName.PULSE2))

        assert render_slots(grid.controller, position) == ".. 01 .. .."
        assert render_frame(grid.logic)[0] == ".. ... . | .. +02 . | .. ... . | .. ... ."

    def test_a_wholly_mixed_block_leaves_a_frame_with_no_patterns_at_all(self, grid: Grid) -> None:
        position = grid.controller.project.song.order_length()
        grid.controller.append_frame()
        grid.logic.select_frame(position)

        block = parse_block(
            ("? ? ?",),
            first_subcolumn=SubColumn.INSTRUMENT,
            sample_ids=grid.sample_ids,
        )
        grid.writer.write(block, TrackerCell(row=0, generator=GeneratorName.PULSE2))

        assert render_slots(grid.controller, position) == ".. .. .. .."


def _typed_grid() -> SequencerTrackerLogic:
    """A second frame of the same shape, reached through the single-slot edits alone."""
    logic = SequencerTrackerLogic(ProjectController(ProjectManager()))
    logic.set_rows_per_pattern(FRAME_ROWS)
    return logic
