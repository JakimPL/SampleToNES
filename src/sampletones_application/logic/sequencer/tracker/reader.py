from collections.abc import Hashable
from typing import Callable, Dict, Optional, TypeVar

from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.slot import (
    column_slot_base,
    slot_from_flat,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.row import Row
from sampletones_shared.utils.agreement import Agreement

from .block import BlockKey, BlockNote, TrackerBlock
from .tracker import SequencerTrackerLogic

ValueT = TypeVar("ValueT", bound=Hashable)


class TrackerBlockReader:
    """Reads a selected region of the shown frame into a block a paste can replay.

    The block is anchored at the column the region begins in, so it carries offsets rather than
    grid coordinates and lands wherever it is written by the kind of each subcolumn.
    """

    def __init__(self, tracker_logic: SequencerTrackerLogic) -> None:
        self._tracker = tracker_logic

    def read(self, region: TrackerRegion) -> TrackerBlock:
        """Takes the values a region covers, keeping each kind of subcolumn in a map of its own."""
        base = column_slot_base(slot_from_flat(region.first_slot).generator)
        return TrackerBlock(
            notes=self._read_subcolumn(region, base, SubColumn.INSTRUMENT, self._note_of),
            transposes=self._read_subcolumn(region, base, SubColumn.TRANSPOSE, self._transpose_of),
            volumes=self._read_subcolumn(region, base, SubColumn.VOLUME, self._volume_of),
        )

    def _read_subcolumn(
        self,
        region: TrackerRegion,
        base: int,
        subcolumn: SubColumn,
        select: Callable[[Optional[Row]], ValueT],
    ) -> Dict[BlockKey, ValueT]:
        """The values one kind of subcolumn holds across a region, keyed by the offsets it stands at.

        A cell holding a definite value keeps it, an empty one keeps its emptiness, and a cell
        whose channels disagree leaves its key out — which is what carries the sample column's
        mixed reading over as a value the paste passes by.
        """
        values: Dict[BlockKey, ValueT] = {}
        for row_offset, row_index in enumerate(region.rows):
            for position, slot in enumerate(region.slots):
                if slot.subcolumn is not subcolumn:
                    continue

                agreement = self._agree(row_index, slot.generator, select)
                if agreement.is_unanimous:
                    values[(row_offset, region.first_slot + position - base)] = agreement.value

        return values

    def _agree(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        select: Callable[[Optional[Row]], ValueT],
    ) -> Agreement[ValueT]:
        """What a column holds at a cell: a channel's own value, or the one its channels share.

        A channel column answers for itself, so it is a group of one and always agrees. The sample
        column answers for the channels it governs, which is the group its display summarises too,
        so a block states about a cell exactly what the grid it came from shows there.
        """
        if generator is not None:
            return Agreement.collapse([select(self._tracker.row(generator, row_index))])

        return Agreement.collapse(
            select(self._tracker.row(channel, row_index)) for channel in self._tracker.relevant_generators(row_index)
        )

    @staticmethod
    def _note_of(row: Optional[Row]) -> Optional[BlockNote]:
        """The note a row carries: the id of the sample it names, or the cut it holds.

        A sample is taken by id so the note keeps its pitch and takes the channel of whichever
        column it is written into.
        """
        match row.command if row is not None else None:
            case Instrument() as instrument:
                return instrument.sample_id
            case NoteOff() as note_off:
                return note_off
            case None:
                return None

    @staticmethod
    def _transpose_of(row: Optional[Row]) -> Optional[int]:
        return row.transpose if row is not None else None

    @staticmethod
    def _volume_of(row: Optional[Row]) -> Optional[int]:
        return row.volume if row is not None else None
