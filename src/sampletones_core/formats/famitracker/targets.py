from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import NUM_PERIODS
from sampletones_core.exporters.rows.pitch import highest_step, written_pitch
from sampletones_core.exporters.slices import InstrumentSlot, InstrumentTable
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.pattern import NoteCell
from sampletones_core.formats.famitracker.notes import period_to_note_cell, pitch_to_note_cell
from sampletones_core.formats.famitracker.specification.patterns import FT_MAX_PITCH, FT_MIN_PITCH
from sampletones_core.formats.famitracker.specification.sequences import SequenceKind


@dataclass(frozen=True)
class RowTarget:
    """The instrument a row naming a voice on one channel triggers, with what places its note.

    Attributes:
        slot: The instrument's position in the module and the reference a row's transpose steps from.
        contour_top: The highest semitone step the instrument's arpeggio moves the note by.
    """

    slot: InstrumentSlot
    contour_top: int

    def cell_pitch(self, transpose: int, channel_name: ChannelName) -> int:
        """The note a cell triggering the instrument at ``transpose`` names, which the channel then holds.

        The noise channel reads its note as a period, wrapped into the sixteen it has. Every other
        channel reads the note its arpeggio moves, so the transposed pitch is written at the note that
        keeps the contour where the song plays it — see :func:`written_pitch` — within the notes a
        cell names.

        Args:
            transpose: The row's transpose, measured from the instrument's reference.
            channel_name: The channel the row stands on.

        Returns:
            int: The pitch the cell names, or the period on noise.
        """
        pitch = self.slot.initial_pitch + transpose
        if channel_name == ChannelName.NOISE:
            return pitch % NUM_PERIODS

        return max(FT_MIN_PITCH, min(FT_MAX_PITCH, written_pitch(pitch, self.contour_top)))

    def note_cell(self, transpose: int, channel_name: ChannelName) -> NoteCell:
        """The note column a row triggering the instrument at ``transpose`` writes."""
        pitch = self.cell_pitch(transpose, channel_name)
        if channel_name == ChannelName.NOISE:
            return period_to_note_cell(pitch)

        return pitch_to_note_cell(pitch)


RowTargets = Dict[Tuple[str, ChannelName], RowTarget]


def row_targets(
    instruments: Sequence[Instrument2A03],
    slots: InstrumentTable,
) -> RowTargets:
    """Pairs every slot a row resolves through with the highest step its instrument's arpeggio reaches.

    The arpeggio is read as the module stores it, so the step is one FamiTracker plays.

    Args:
        instruments: The module's instruments.
        slots: The slot a row naming a voice on a channel resolves through.

    Returns:
        RowTargets: What each row naming a voice on a channel triggers.
    """
    contour_tops = {
        instrument.index: highest_step(instrument.sequences[SequenceKind.ARPEGGIO].items) for instrument in instruments
    }
    return {
        key: RowTarget(
            slot=slot,
            contour_top=contour_tops[slot.index],
        )
        for key, slot in slots.items()
    }
