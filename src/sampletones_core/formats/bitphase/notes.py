from sampletones_core.constants.general import NUM_PERIODS
from sampletones_core.formats.bitphase.model.pattern import NoteCell
from sampletones_core.formats.bitphase.specification.patterns import (
    FIRST_OCTAVE,
    MAX_NOTE_INDEX,
    MIN_NOTE_INDEX,
    NOISE_BASE_NOTE_INDEX,
    NOTE_INDEX_PITCH_OFFSET,
    NOTE_RANGE,
    NoteName,
)


def pitch_to_note_index(pitch: int) -> int:
    """Converts an absolute pitch to the note index Bitphase tunes from.

    The index is clamped to the span the 96-entry tuning table covers, so an extreme
    transposition lands on the nearest playable note.

    Args:
        pitch: Absolute pitch, on the same scale the reconstruction records.

    Returns:
        int: Index into the tuning table.
    """
    index = pitch - NOTE_INDEX_PITCH_OFFSET
    return max(MIN_NOTE_INDEX, min(MAX_NOTE_INDEX, index))


def note_index_to_note_cell(index: int) -> NoteCell:
    """Converts a tuning-table index to the note and octave a pattern cell stores.

    Args:
        index: Index into the tuning table.

    Returns:
        NoteCell: The note column playback resolves back to ``index``.
    """
    name = index % NOTE_RANGE + int(NoteName.C)
    octave = index // NOTE_RANGE + FIRST_OCTAVE
    return NoteCell(name=name, octave=octave)


def noise_period_to_note_index(period: int) -> int:
    """Converts a noise period index to the note index that selects it.

    The project counts noise periods from the slowest and the register counts them from the
    fastest, so a period reaches the register as ``15 - period``. Playback writes
    ``15 - (index mod 16)`` to the register for a noise note, so the note index carries the
    period itself, wrapped into the sixteen the channel has. Every period repeats once per
    sixteen note indices, and the base index sits far enough below the top of the tuning
    table that a whole cycle of table offsets stays in range.

    Args:
        period: Noise period index the reconstruction chose, or one a transpose moved.

    Returns:
        int: Note index that sounds ``period``.
    """
    return NOISE_BASE_NOTE_INDEX + period % NUM_PERIODS


def noise_arpeggio_to_table_offset(step: int) -> int:
    """Converts a noise arpeggio step to the semitone offset a table row carries.

    The note index carries the period itself (see :func:`noise_period_to_note_index`), so a
    step moves the index by as much, wrapped into one period cycle, which keeps every note
    the table reaches inside the tuning table.

    Args:
        step: Period offset from the reconstruction's initial noise period.

    Returns:
        int: Semitone offset that moves the noise period by ``step``.
    """
    return step % NUM_PERIODS
