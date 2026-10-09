from typing import Final, Optional, Union

from sampletones_core.constants.general import MAX_PERIOD
from sampletones_core.project.patterns.pitch import Note, RowPitch, Step
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_core.structures import IdentifiedCollection
from sampletones_core.utils.frequencies import period_to_name, pitch_to_name, played_pitch
from sampletones_shared.constants.symbols import MINUS, PLUS

DEFAULT_DISPLAY_LENGTH: Final[int] = 2

BLANK: Final[str] = "."
NOTE_OFF: Final[str] = "~~"
NOTE_BLANK: Final[str] = "..."


def display_value(
    value: Optional[int],
    *,
    length: int = DEFAULT_DISPLAY_LENGTH,
    hexadecimal: bool = True,
) -> str:
    if value is None:
        return BLANK * length

    if hexadecimal:
        return f"{value:0{length}X}"

    return f"{value:0{length}d}"


def display_id(value: Optional[int]) -> str:
    return display_value(value, hexadecimal=True)


def display_voice(
    *,
    voices: IdentifiedCollection[VoiceUnion],
    voice_id: Optional[str] = None,
) -> str:
    """
    Render a voice reference as its current list position (not its uuid).
    """
    if voice_id is not None and voices.get(voice_id) is not None:
        return display_id(voices.get_index(voice_id))

    return display_id(None)


def display_voice_label(position: int, name: str) -> str:
    """Render a voice's list label as ``"<hex position>: <name>"`` (e.g. ``"1A: Bass"``)."""
    return f"{display_id(position)}: {name}"


def display_command(
    voices: IdentifiedCollection[VoiceUnion],
    command: Optional[Union[NoteOn, NoteOff]],
) -> str:
    """Render a row's note-column command: a voice's list position, ``--`` for note-off, or ``..``."""
    match command:
        case NoteOff():
            return NOTE_OFF
        case NoteOn():
            return display_voice(voices=voices, voice_id=command.voice_id)
        case None:
            return display_voice(voices=voices, voice_id=None)


def display_volume(value: Optional[int]) -> str:
    return display_value(value, length=1, hexadecimal=True)


def display_pitch(pitch: Optional[RowPitch]) -> str:
    """Render a pitch column as the face it was written in, or ``...`` for an empty one.

    A note prints as its name and a step as a signed offset, so the grid shows what the reader
    typed whichever voice the row names. A note's value names a period while it lies among the
    sixteen the noise channel has, and a pitch above them; the two ranges stand apart, so the name
    needs no channel. A pitch below the lowest note a channel plays prints as that note, the way
    the channel sounds it.

    Args:
        pitch: The pitch the row states, or ``None`` for an empty cell.

    Returns:
        str: The note name or the signed step, three characters wide like every other reading of
            the column.
    """
    match pitch:
        case None:
            return NOTE_BLANK
        case Step():
            return display_transpose(pitch.value)
        case Note():
            if pitch.value <= MAX_PERIOD:
                return period_to_name(pitch.value)

            return pitch_to_name(played_pitch(pitch.value))


def display_transpose(value: Optional[int]) -> str:
    """Render a step as a signed two-digit decimal offset, or ``...`` for an empty one.

    An explicit zero reads ``+00``, since a row storing it moves the voice back to its own pitch,
    while an empty cell keeps whatever pitch is already in force. Decimal digits keep every step a
    reader can type on the digit keys alone, and read as the semitones a musician counts.
    """
    if value is None:
        return NOTE_BLANK

    sign = PLUS if value >= 0 else MINUS
    return f"{sign}{abs(value):02d}"
