from dataclasses import dataclass
from typing import Dict, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.rows.pitch import highest_step, written_pitch
from sampletones_core.formats.bitphase.model.instrument import BitphaseInstrument
from sampletones_core.formats.bitphase.model.table import BitphaseTable
from sampletones_core.formats.bitphase.notes import noise_period_to_note_index, pitch_to_note_index


@dataclass(frozen=True)
class SliceVoice:
    """One built instrument together with the table and the note that triggers it.

    Attributes:
        number: Value a pattern's instrument column carries to play the instrument.
        instrument: The macros the channel reads a value per tick from.
        table: The per-tick semitone contour that moves the note.
        channel: The NES channel the slice was reconstructed for.
        initial_pitch: Pitch the slice's contour is measured against.
        ticks: How many ticks the instrument runs before every dimension stands at its end.
    """

    number: int
    instrument: BitphaseInstrument
    table: BitphaseTable
    channel: ChannelName
    initial_pitch: int
    ticks: int

    @property
    def contour_top(self) -> int:
        """The highest semitone step the slice's table moves its note by."""
        return highest_step(self.table.rows)

    def note_index(self, transpose: int) -> int:
        """The note index a row triggering the slice at ``transpose`` writes.

        The noise channel reads its note as a period selector, so its transposed period takes the
        index that sounds that period. Every other channel reads the tuning table at the note its
        table moves, so the transposed pitch is written at the note that keeps the contour where the
        song plays it — see :func:`written_pitch`.

        Args:
            transpose: The semitone offset the row moves the slice by, or the period offset on noise.

        Returns:
            int: The index the row's note column names.
        """
        pitch = self.initial_pitch + transpose
        if self.channel == ChannelName.NOISE:
            return noise_period_to_note_index(pitch)

        return pitch_to_note_index(written_pitch(pitch, self.contour_top))


SliceVoiceTable = Dict[Tuple[str, ChannelName], SliceVoice]
