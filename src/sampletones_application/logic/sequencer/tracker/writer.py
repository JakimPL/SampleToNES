from typing import Callable, Dict, Optional, TypeVar

from sampletones_application.logic.sequencer.tracker.block import (
    BlockKey,
    BlockNote,
    TrackerBlock,
)
from sampletones_application.logic.sequencer.tracker.tracker import (
    SequencerTrackerLogic,
)
from sampletones_application.view_model.sequencer.region import (
    TrackerCell,
    TrackerRegion,
)
from sampletones_application.view_model.sequencer.slot import (
    SLOT_COUNT,
    column_slot_base,
    slot_from_flat,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.note_off import NoteOff

ValueT = TypeVar("ValueT")


class TrackerBlockWriter:
    """Replays a block into the shown frame, and empties the cells a region covers.

    Every cell reaches the grid through the single-slot edit that already governs it, so a paste
    lands exactly the writes a reader typing the same values by hand would make, sample column
    included.
    """

    def __init__(self, tracker_logic: SequencerTrackerLogic) -> None:
        self._tracker = tracker_logic

    def write(self, block: TrackerBlock, cell: TrackerCell) -> None:
        """Writes a block anchored at a cell, the cell supplying the column and the block the rest.

        Each kind of subcolumn is written in a pass of its own, notes first: a note through the
        sample column decides the whole row, so the transposes and volumes sharing that row land
        on top of the channels it settled.
        """
        base = column_slot_base(cell.generator)
        self._write_pass(block.notes, cell, base, self._write_note)
        self._write_pass(block.transposes, cell, base, self._write_transpose)
        self._write_pass(block.volumes, cell, base, self._write_volume)

    def clear(self, region: TrackerRegion) -> None:
        """Empties every subcolumn a region covers, each by the rule its own column follows."""
        for row_index in region.rows:
            for slot in region.slots:
                self._tracker.clear_cell_subcolumn(
                    row_index,
                    slot.generator,
                    slot.subcolumn,
                )

    def _write_pass(
        self,
        values: Dict[BlockKey, ValueT],
        cell: TrackerCell,
        base: int,
        write: Callable[[int, Optional[GeneratorName], ValueT], None],
    ) -> None:
        """Writes one kind of subcolumn across the block, dropping what falls outside the grid.

        Keys are taken in reading order, so a row's sample column is written before the channels
        beside it and the more specific write is the one that stands. A row past the frame's last
        or a slot past the last column is left out, which clips a block at the edge rather than
        wrapping it around.
        """
        row_count = self._tracker.frame_row_count()
        for (row_offset, slot_offset), value in sorted(values.items()):
            row_index = cell.row + row_offset
            slot_index = base + slot_offset
            if row_index >= row_count or slot_index >= SLOT_COUNT:
                continue

            write(row_index, slot_from_flat(slot_index).generator, value)

    def _write_note(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        note: Optional[BlockNote],
    ) -> None:
        """Writes the note a cell carries: a sample by id, a cut, or the emptiness of neither.

        A sample the project no longer holds leaves the cell as it stands, so a block outliving
        the project it was read from writes the notes that still name something and passes over
        the rest.
        """
        match note:
            case NoteOff():
                self._tracker.cut_note(row_index, generator)
            case str() as sample_id:
                if self._tracker.holds_sample(sample_id):
                    self._tracker.place_note(row_index, generator, sample_id)
            case None:
                self._tracker.clear_cell_subcolumn(
                    row_index,
                    generator,
                    SubColumn.INSTRUMENT,
                )

    def _write_transpose(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        transpose: Optional[int],
    ) -> None:
        if transpose is None:
            self._tracker.clear_cell_subcolumn(
                row_index,
                generator,
                SubColumn.TRANSPOSE,
            )
        else:
            self._tracker.set_cell_subcolumn(
                row_index,
                generator,
                transpose=transpose,
            )

    def _write_volume(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        volume: Optional[int],
    ) -> None:
        if volume is None:
            self._tracker.clear_cell_subcolumn(
                row_index,
                generator,
                SubColumn.VOLUME,
            )
        else:
            self._tracker.set_cell_subcolumn(
                row_index,
                generator,
                volume=volume,
            )
