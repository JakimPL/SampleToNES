from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Final, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.rows.transpose import SoundingNote, sounding_notes
from sampletones_core.formats.bitphase.model.pattern import EffectCell
from sampletones_core.formats.bitphase.model.table import BitphaseTable
from sampletones_core.formats.bitphase.specification.effects import (
    MAX_ORNAMENT_POSITION,
    NO_EFFECT_TABLE,
    ORNAMENT_POSITION_DELAY,
    EffectId,
)
from sampletones_core.formats.bitphase.specification.instruments import FIRST_TABLE_STEP, MAX_TABLE_ID
from sampletones_core.formats.bitphase.specification.patterns import TABLE_COLUMN_OFFSET
from sampletones_core.formats.bitphase.voices import SliceVoice, SliceVoiceTable
from sampletones_core.project.song import Song
from sampletones_core.timing import SongTiming

NOTE_SHIFT: Final[int] = 0
MOVED_TABLE_NAME: Final[str] = "{name} {shift:+d}"
STARTED_TABLE_NAME: Final[str] = "{name} {shift:+d} from {start}"
NO_EFFECTS: Final[Tuple[Optional[EffectCell], ...]] = (None,)

TableKey = Tuple[int, int, int]


@dataclass(frozen=True)
class TransposeCell:
    """The columns a transpose row writes: the table that moves the note, and where it starts.

    Attributes:
        table: The table column naming the moved table.
        effects: The row's effect columns, placing the table at the step the note has reached.
    """

    table: int
    effects: Tuple[Optional[EffectCell], ...]


@dataclass
class _TableShelf:
    """The moved tables a document holds, numbered from the first id its other tables leave free.

    Attributes:
        first_id: The id the first moved table takes.
        tables: The moved tables, by the slice, the shift and the step each opens on.
    """

    first_id: int
    tables: Dict[TableKey, BitphaseTable] = field(default_factory=dict)

    def table(self, voice: SliceVoice, shift: int, start: int) -> BitphaseTable:
        """The slice's table moved by ``shift`` and opening on ``start``, shared by every row asking for it.

        A shift of none opening on the first step is the slice's own table.

        Raises:
            ValueError: If the table would take an id past the ones the table column names.
        """
        if shift == NOTE_SHIFT and start == FIRST_TABLE_STEP:
            return voice.table

        key = (voice.number, shift, start)
        if key not in self.tables:
            table_id = self.first_id + len(self.tables)
            if table_id > MAX_TABLE_ID:
                raise ValueError(
                    f"Document exceeds the Bitphase limit of {MAX_TABLE_ID + 1} tables "
                    f"once its transpose rows take tables of their own"
                )

            self.tables[key] = voice.table.moved(
                table_id=table_id,
                shift=shift,
                start=start,
                name=self._name(voice, shift, start),
            )

        return self.tables[key]

    @staticmethod
    def _name(voice: SliceVoice, shift: int, start: int) -> str:
        if start == FIRST_TABLE_STEP:
            return MOVED_TABLE_NAME.format(name=voice.table.name, shift=shift)

        return STARTED_TABLE_NAME.format(name=voice.table.name, shift=shift, start=start)


def _ornament_position(position: int) -> Tuple[Optional[EffectCell], ...]:
    """The effect columns placing a newly attached table at ``position``, which the first step needs none of."""
    if position == FIRST_TABLE_STEP:
        return NO_EFFECTS

    return (
        EffectCell(
            effect=int(EffectId.ORNAMENT_POSITION),
            delay=ORNAMENT_POSITION_DELAY,
            parameter=position,
            table_index=NO_EFFECT_TABLE,
        ),
    )


@dataclass(frozen=True)
class TransposePlan:
    """The cells a document's transpose rows write, and the moved tables those cells name.

    Bitphase restarts the instrument on a note or an instrument cell, and a table cell alone attaches
    a table at its first step while the instrument plays on. A transpose row therefore names a copy
    of the note's table moved by the distance between the note its transpose would write and the
    note already written, and an ornament-position effect places that copy at the step the note's
    own table has reached. From that tick the channel sounds what a note-on at the new transpose
    would sound, with the instrument's envelopes going on where they stood.

    Attributes:
        cells: Per channel, the cell each transpose row writes, keyed by its frame and row.
        tables: The moved tables the cells name, in id order.
    """

    cells: Dict[ChannelName, Dict[Tuple[int, int], TransposeCell]]
    tables: Tuple[BitphaseTable, ...]

    @classmethod
    def build(
        cls,
        song: Song,
        voices: SliceVoiceTable,
        timing: SongTiming,
        *,
        first_table_id: int,
    ) -> TransposePlan:
        """Plans every transpose row of the song, following the notes the order sounds.

        A note's table advances a step every tick, so the step a transpose row reaches is read from
        the ticks the song's timing gives every row since the note, across frames. An ornament position
        names a step up to ``MAX_ORNAMENT_POSITION``, so a row reaching a later step names a copy of
        the table opening on that step. A row keeping the shift the channel already carries
        writes nothing.

        Args:
            song: The arrangement being exported.
            voices: The slices a row's note-on reaches, by voice and channel.
            timing: How many ticks every row of the song lasts in the document.
            first_table_id: The id the first moved table takes, above every other table.

        Returns:
            TransposePlan: The cells and the moved tables they name.

        Raises:
            ValueError: If the moved tables run past the ids the table column names.
        """
        shelf = _TableShelf(first_id=first_table_id)
        cells: Dict[ChannelName, Dict[Tuple[int, int], TransposeCell]] = {}
        for channel_name in ChannelName.items():
            channel_cells: Dict[Tuple[int, int], TransposeCell] = {}
            for note in sounding_notes(song, channel_name, voices):
                channel_cells.update(
                    cls._note_cells(
                        note,
                        voices[(note.voice_id, channel_name)],
                        timing,
                        song.order_length(),
                        shelf,
                    )
                )

            cells[channel_name] = channel_cells

        return cls(cells=cells, tables=tuple(shelf.tables.values()))

    def frame_cells(self, channel_name: ChannelName, order_position: int) -> Dict[int, TransposeCell]:
        """The cells one frame's transpose rows on a channel write, keyed by row."""
        return {
            row_index: cell
            for (position, row_index), cell in self.cells[channel_name].items()
            if position == order_position
        }

    @staticmethod
    def _note_cells(
        note: SoundingNote,
        voice: SliceVoice,
        timing: SongTiming,
        frames: int,
        shelf: _TableShelf,
    ) -> Dict[Tuple[int, int], TransposeCell]:
        """The cells the transpose rows reaching one note write."""
        written = voice.note_index(note.transpose)
        carried = NOTE_SHIFT
        cells: Dict[Tuple[int, int], TransposeCell] = {}
        for repitch in note.repitches:
            shift = voice.note_index(repitch.transpose) - written
            if shift == carried:
                continue

            carried = shift
            position = voice.table.position_at(
                timing.ticks_across(
                    note.place.order_position,
                    note.place.row_index,
                    repitch.rows,
                    frames=frames,
                )
            )
            cells[(repitch.place.order_position, repitch.place.row_index)] = TransposePlan._attached(
                voice,
                shift,
                position,
                shelf,
            )

        return cells

    @staticmethod
    def _attached(
        voice: SliceVoice,
        shift: int,
        position: int,
        shelf: _TableShelf,
    ) -> TransposeCell:
        """The cell attaching the slice's table moved by ``shift`` at the step ``position``.

        An ornament position places the moved table where it names a step, and a table opening on
        the step itself carries a later one.
        """
        if position <= MAX_ORNAMENT_POSITION:
            table = shelf.table(voice, shift, FIRST_TABLE_STEP)
            return TransposeCell(table=table.id + TABLE_COLUMN_OFFSET, effects=_ornament_position(position))

        table = shelf.table(voice, shift, position)
        return TransposeCell(table=table.id + TABLE_COLUMN_OFFSET, effects=NO_EFFECTS)
