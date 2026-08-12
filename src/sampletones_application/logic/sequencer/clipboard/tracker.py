from typing import Callable, Dict, Final, List, Optional

from sampletones_application.logic.sequencer.tracker.block import (
    BlockKey,
    BlockNote,
    TrackerBlock,
)
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.slot import (
    SLOT_COUNT,
    column_slot_base,
    slot_from_flat,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.general import (
    MAX_TRANSPOSE,
    MAX_VOLUME,
    MIN_TRANSPOSE,
    SILENT_VOLUME,
)
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.utils.display import (
    NOTE_OFF,
    display_id,
    display_transpose,
    display_volume,
)
from sampletones_shared.constants.symbols import PLUS, SIGNS

from .fields import (
    FieldReading,
    read_hexadecimal,
    read_placeholder,
    state_mixed,
    store_reading,
)
from .header import BlockShape, parse_header, state_header
from .samples import SampleDirectory

TRACKER_GRID: Final[str] = "tracker"
SLOT_KEY: Final[str] = "slots"
COLUMN_SEPARATOR: Final[str] = "|"
NOTE_WIDTH: Final[int] = len(display_id(None))
TRANSPOSE_WIDTH: Final[int] = len(display_transpose(None))
VOLUME_WIDTH: Final[int] = len(display_volume(None))


class TrackerBlockText:
    """States a tracker block as the lines the grid prints, and reads the same form back.

    Every field carries what the grid shows in its cell, which is what makes the three states a
    cell reaches a block in survive a round trip: a value reads as its value, an empty cell as
    the dots beneath it, and a mixed one as the marks filling its field. A bar stands between
    columns, so a line reads as the row it was taken from.

    A note names its sample by the list position the grid prints, so a block carried to another
    project plays whichever sample stands at that position there.
    """

    def __init__(self, *, samples: SampleDirectory) -> None:
        self._samples = samples

    def state(self, block: TrackerBlock, region: TrackerRegion) -> str:
        """The text a copy puts on the system clipboard, the region supplying the shape.

        The region is what states the slots the block stands on, since a mixed cell leaves its
        key out and a block alone therefore names less than the rectangle it was read from.
        """
        shape = BlockShape(
            rows=len(region.rows),
            first=region.first_slot,
            last=region.last_slot,
        )
        lines = [state_header(grid=TRACKER_GRID, span_key=SLOT_KEY, shape=shape)]
        lines.extend(
            self._state_row(
                block,
                region,
                row_offset,
            )
            for row_offset in range(shape.rows)
        )
        return "\n".join(lines)

    def parse(self, text: str) -> Optional[TrackerBlock]:
        """The block a text states, present while it is one this grid writes.

        Text naming another grid, declaring a shape its lines do not fill, or carrying a field
        the form has no reading for states no block, so the slot the tracker copied into stands.
        """
        lines = text.strip().splitlines()
        if not lines:
            return None

        shape = parse_header(lines[0], grid=TRACKER_GRID, span_key=SLOT_KEY)
        if shape is None or shape.last >= SLOT_COUNT or len(lines) != shape.rows + 1:
            return None

        return self._read_rows(lines[1:], shape)

    def _state_row(
        self,
        block: TrackerBlock,
        region: TrackerRegion,
        row_offset: int,
    ) -> str:
        """One row of the block, its fields in slot order and its columns held apart by a bar."""
        base = column_slot_base(slot_from_flat(region.first_slot).generator)
        fields: List[str] = []
        for position, slot in enumerate(region.slots):
            if position > 0 and slot.generator != region.slots[position - 1].generator:
                fields.append(COLUMN_SEPARATOR)

            key = (row_offset, region.first_slot + position - base)
            fields.append(self._state_slot(block, slot.subcolumn, key))

        return " ".join(fields)

    def _state_slot(
        self,
        block: TrackerBlock,
        subcolumn: SubColumn,
        key: BlockKey,
    ) -> str:
        match subcolumn:
            case SubColumn.INSTRUMENT:
                return self._state_note(block.notes, key)
            case SubColumn.TRANSPOSE:
                return self._state_number(
                    block.transposes,
                    key,
                    display_transpose,
                    TRANSPOSE_WIDTH,
                )
            case SubColumn.VOLUME:
                return self._state_number(
                    block.volumes,
                    key,
                    display_volume,
                    VOLUME_WIDTH,
                )

    def _state_note(
        self,
        notes: Dict[BlockKey, Optional[BlockNote]],
        key: BlockKey,
    ) -> str:
        """What the note column prints at a cell, a sample naming the position it stands at.

        A note whose sample the project in place lacks prints as mixed, so reading the text back
        passes that cell by, the way a paste passes over a sample it has nothing to place.
        """
        if key not in notes:
            return state_mixed(NOTE_WIDTH)

        match notes[key]:
            case NoteOff():
                return NOTE_OFF
            case str() as sample_id:
                position = self._samples.position_of(sample_id)
                return state_mixed(NOTE_WIDTH) if position is None else display_id(position)
            case _:
                return display_id(None)

    @staticmethod
    def _state_number(
        values: Dict[BlockKey, Optional[int]],
        key: BlockKey,
        display: Callable[[Optional[int]], str],
        width: int,
    ) -> str:
        if key not in values:
            return state_mixed(width)

        return display(values[key])

    def _read_rows(
        self,
        lines: List[str],
        shape: BlockShape,
    ) -> Optional[TrackerBlock]:
        """The block a body states, each kind of subcolumn gathered into a map of its own."""
        base = column_slot_base(slot_from_flat(shape.first).generator)
        notes: Dict[BlockKey, Optional[BlockNote]] = {}
        transposes: Dict[BlockKey, Optional[int]] = {}
        volumes: Dict[BlockKey, Optional[int]] = {}
        for row_offset, line in enumerate(lines):
            fields = line.replace(COLUMN_SEPARATOR, " ").split()
            if len(fields) != shape.width:
                return None

            for position, field in enumerate(fields):
                slot = slot_from_flat(shape.first + position)
                key = (row_offset, shape.first + position - base)
                match slot.subcolumn:
                    case SubColumn.INSTRUMENT:
                        read = store_reading(
                            notes,
                            key,
                            self._read_note(field),
                        )
                    case SubColumn.TRANSPOSE:
                        read = store_reading(
                            transposes,
                            key,
                            self._read_transpose(field),
                        )
                    case SubColumn.VOLUME:
                        read = store_reading(
                            volumes,
                            key,
                            self._read_volume(field),
                        )

                if not read:
                    return None

        return TrackerBlock(
            notes=notes,
            transposes=transposes,
            volumes=volumes,
        )

    def _read_note(self, field: str) -> Optional[FieldReading[BlockNote]]:
        """The note a field states: the sample standing at the position it names, a cut, or emptiness.

        A position the project's samples fall short of states nothing, so a paste passes that
        cell by rather than silencing it.
        """
        placeholder: Optional[FieldReading[BlockNote]] = read_placeholder(field)
        if placeholder is not None:
            return placeholder

        if field == NOTE_OFF:
            return FieldReading.of(NoteOff())

        position = read_hexadecimal(field)
        if position is None:
            return None

        sample_id = self._samples.sample_at(position)
        return FieldReading.mixed() if sample_id is None else FieldReading.of(sample_id)

    @staticmethod
    def _read_transpose(field: str) -> Optional[FieldReading[int]]:
        """The transpose a signed field states, present while it lies in the range a row accepts."""
        placeholder: Optional[FieldReading[int]] = read_placeholder(field)
        if placeholder is not None:
            return placeholder

        sign = field[:1]
        magnitude = read_hexadecimal(field[1:])
        if sign not in SIGNS or magnitude is None:
            return None

        transpose = magnitude if sign == PLUS else -magnitude
        if not MIN_TRANSPOSE <= transpose <= MAX_TRANSPOSE:
            return None

        return FieldReading.of(transpose)

    @staticmethod
    def _read_volume(field: str) -> Optional[FieldReading[int]]:
        """The volume a field states, present while it lies in the range a row accepts."""
        placeholder: Optional[FieldReading[int]] = read_placeholder(field)
        if placeholder is not None:
            return placeholder

        volume = read_hexadecimal(field)
        if volume is None or not SILENT_VOLUME <= volume <= MAX_VOLUME:
            return None

        return FieldReading.of(volume)
