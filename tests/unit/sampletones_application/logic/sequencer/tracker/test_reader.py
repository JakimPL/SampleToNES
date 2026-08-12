from typing import Optional, Tuple

import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.tracker import (
    SequencerTrackerLogic,
    TrackerBlockReader,
)
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.slot import SUBCOLUMNS, TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.note_off import NoteOff
from tests.suite.sequencer import sample_reconstruction


def _key(subcolumn: SubColumn, row_offset: int = 0) -> Tuple[int, int]:
    """Where a subcolumn's value stands in a block read from the column it belongs to.

    Offsets run from the base of that column, so a subcolumn's own place in the column is the
    slot offset it reaches the block at.
    """
    return (row_offset, SUBCOLUMNS.index(subcolumn))


@pytest.fixture
def controller() -> ProjectController:
    """A controller over a fresh project, which the samples a test places are added to."""
    return ProjectController(ProjectManager())


@pytest.fixture
def logic(controller: ProjectController) -> SequencerTrackerLogic:
    """The tracker logic the reader takes every value through."""
    return SequencerTrackerLogic(controller)


@pytest.fixture
def reader(logic: SequencerTrackerLogic) -> TrackerBlockReader:
    return TrackerBlockReader(logic)


def _slot(generator: Optional[GeneratorName], subcolumn: SubColumn) -> int:
    return TrackerSlot(generator, subcolumn).flat_index


def _cell(
    row_index: int,
    generator: Optional[GeneratorName],
    subcolumn: SubColumn,
) -> TrackerRegion:
    """The region one subcolumn of one cell covers."""
    slot = _slot(generator, subcolumn)
    return TrackerRegion(
        first_row=row_index,
        last_row=row_index,
        first_slot=slot,
        last_slot=slot,
    )


def _column(
    generator: Optional[GeneratorName],
    *,
    last_row: int = 0,
) -> TrackerRegion:
    """The region one whole column covers, down to ``last_row``."""
    return TrackerRegion(
        first_row=0,
        last_row=last_row,
        first_slot=_slot(generator, SubColumn.INSTRUMENT),
        last_slot=_slot(generator, SubColumn.VOLUME),
    )


class TestChannelColumn:
    """A channel answers for itself, so every one of its cells reaches the block definite."""

    def test_a_cell_carries_the_values_it_holds(
        self,
        controller: ProjectController,
        logic: SequencerTrackerLogic,
        reader: TrackerBlockReader,
    ) -> None:
        sample = controller.add_sample(
            sample_reconstruction([GeneratorName.PULSE1]),
            name="lead",
        )
        logic.place_note(0, GeneratorName.PULSE1, sample.id)
        logic.set_cell_subcolumn(0, GeneratorName.PULSE1, transpose=5, volume=3)

        block = reader.read(_column(GeneratorName.PULSE1))

        assert block.notes[_key(SubColumn.INSTRUMENT)] == sample.id
        assert block.transposes[_key(SubColumn.TRANSPOSE)] == 5
        assert block.volumes[_key(SubColumn.VOLUME)] == 3

    def test_an_empty_cell_carries_its_emptiness(
        self,
        reader: TrackerBlockReader,
    ) -> None:
        """An untouched channel holds no pattern at all, which reads as the empty cell it shows."""
        block = reader.read(_column(GeneratorName.NOISE))

        assert block.notes[_key(SubColumn.INSTRUMENT)] is None
        assert block.transposes[_key(SubColumn.TRANSPOSE)] is None
        assert block.volumes[_key(SubColumn.VOLUME)] is None

    def test_a_cut_cell_carries_the_cut(
        self,
        logic: SequencerTrackerLogic,
        reader: TrackerBlockReader,
    ) -> None:
        logic.cut_note(0, GeneratorName.PULSE1)

        block = reader.read(_cell(0, GeneratorName.PULSE1, SubColumn.INSTRUMENT))

        assert block.notes[_key(SubColumn.INSTRUMENT)] == NoteOff()

    def test_a_zero_transpose_carries_as_the_value_it_is(
        self,
        logic: SequencerTrackerLogic,
        reader: TrackerBlockReader,
    ) -> None:
        """An explicit zero resets the channel's transpose, so it is a value and not an absence."""
        logic.set_cell_subcolumn(0, GeneratorName.PULSE2, transpose=0)

        block = reader.read(_cell(0, GeneratorName.PULSE2, SubColumn.TRANSPOSE))

        assert block.transposes[_key(SubColumn.TRANSPOSE)] == 0

    def test_rows_past_the_pattern_read_empty(
        self,
        logic: SequencerTrackerLogic,
        reader: TrackerBlockReader,
    ) -> None:
        """A region reaching past the rows a pattern holds takes emptiness from beyond its end."""
        logic.set_rows_per_pattern(2)
        logic.set_cell_subcolumn(0, GeneratorName.PULSE1, volume=4)

        block = reader.read(_column(GeneratorName.PULSE1, last_row=3))

        assert block.volumes[_key(SubColumn.VOLUME)] == 4
        assert block.volumes[_key(SubColumn.VOLUME, 2)] is None
        assert block.volumes[_key(SubColumn.VOLUME, 3)] is None


class TestSampleColumn:
    """The sample column answers for the channels it governs, agreeing or reading as nothing."""

    def test_a_value_every_governed_channel_shares_carries_over(
        self,
        controller: ProjectController,
        logic: SequencerTrackerLogic,
        reader: TrackerBlockReader,
    ) -> None:
        sample = controller.add_sample(
            sample_reconstruction([GeneratorName.PULSE1, GeneratorName.TRIANGLE]),
            name="lead",
        )
        logic.place_note(0, None, sample.id)
        logic.set_cell_subcolumn(0, None, transpose=7)

        block = reader.read(_column(None))

        assert block.notes[_key(SubColumn.INSTRUMENT)] == sample.id
        assert block.transposes[_key(SubColumn.TRANSPOSE)] == 7

    def test_a_note_carries_as_the_sample_it_names(
        self,
        controller: ProjectController,
        logic: SequencerTrackerLogic,
        reader: TrackerBlockReader,
    ) -> None:
        """The channels hold instruments of their own, and the block keeps the sample they share."""
        sample = controller.add_sample(
            sample_reconstruction([GeneratorName.PULSE1, GeneratorName.PULSE2]),
            name="chord",
        )
        logic.place_note(0, None, sample.id)

        block = reader.read(_cell(0, None, SubColumn.INSTRUMENT))

        assert block.notes[_key(SubColumn.INSTRUMENT)] == sample.id

    def test_a_column_its_channels_disagree_over_leaves_its_key_out(
        self,
        logic: SequencerTrackerLogic,
        reader: TrackerBlockReader,
    ) -> None:
        """No sample governs the row, so the column spans every channel and only one holds a value."""
        logic.set_cell_subcolumn(0, GeneratorName.PULSE1, transpose=5)

        block = reader.read(_cell(0, None, SubColumn.TRANSPOSE))

        assert _key(SubColumn.TRANSPOSE) not in block.transposes

    def test_a_half_cut_row_leaves_its_note_out(
        self,
        logic: SequencerTrackerLogic,
        reader: TrackerBlockReader,
    ) -> None:
        logic.cut_note(0, GeneratorName.PULSE1)

        block = reader.read(_cell(0, None, SubColumn.INSTRUMENT))

        assert _key(SubColumn.INSTRUMENT) not in block.notes

    def test_a_wholly_cut_row_carries_the_cut(
        self,
        logic: SequencerTrackerLogic,
        reader: TrackerBlockReader,
    ) -> None:
        logic.cut_note(0, None)

        block = reader.read(_cell(0, None, SubColumn.INSTRUMENT))

        assert block.notes[_key(SubColumn.INSTRUMENT)] == NoteOff()

    def test_an_untouched_row_carries_its_emptiness(
        self,
        reader: TrackerBlockReader,
    ) -> None:
        """Every channel is equally empty, which is a reading they agree on."""
        block = reader.read(_column(None))

        assert block.notes[_key(SubColumn.INSTRUMENT)] is None
        assert block.transposes[_key(SubColumn.TRANSPOSE)] is None
        assert block.volumes[_key(SubColumn.VOLUME)] is None


class TestOffsets:
    """A block addresses its values by the offsets it was read at, whatever the cells hold."""

    def test_a_mixed_edge_column_leaves_only_itself_out(
        self,
        logic: SequencerTrackerLogic,
        reader: TrackerBlockReader,
    ) -> None:
        """The last slot reads as nothing, and the cells beside it keep the offsets they stand at."""
        logic.set_cell_subcolumn(0, GeneratorName.PULSE1, volume=2)

        block = reader.read(
            TrackerRegion(
                first_row=0,
                last_row=0,
                first_slot=_slot(None, SubColumn.INSTRUMENT),
                last_slot=_slot(None, SubColumn.VOLUME),
            )
        )

        assert set(block.notes) == {_key(SubColumn.INSTRUMENT)}
        assert set(block.transposes) == {_key(SubColumn.TRANSPOSE)}
        assert _key(SubColumn.VOLUME) not in block.volumes

    def test_the_offsets_are_measured_from_the_column_the_block_begins_in(
        self,
        reader: TrackerBlockReader,
    ) -> None:
        """A block beginning midway through a column keeps that column's base as its own zero.

        The offsets stay a whole column apart from the kind they address, which is what lands
        each value in a subcolumn of its own kind wherever the block is written.
        """
        block = reader.read(
            TrackerRegion(
                first_row=0,
                last_row=0,
                first_slot=_slot(GeneratorName.PULSE2, SubColumn.TRANSPOSE),
                last_slot=_slot(GeneratorName.TRIANGLE, SubColumn.INSTRUMENT),
            )
        )

        assert set(block.transposes) == {(0, 1)}
        assert set(block.volumes) == {(0, 2)}
        assert set(block.notes) == {(0, 3)}
