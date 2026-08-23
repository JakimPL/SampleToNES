from typing import Final, Optional, Union

from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.structures import IdentifiedCollection
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
    voices: IdentifiedCollection[Sample],
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
    voices: IdentifiedCollection[Sample],
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


def display_transpose(value: Optional[int]) -> str:
    """Render a transpose as a signed two-digit offset, or ``...`` for an empty one.

    An explicit zero reads ``+00``, since a row storing it resets the channel's
    transpose to the sample's own pitch, while an empty cell keeps whatever
    transpose is already in force.
    """
    if value is None:
        return NOTE_BLANK

    sign = PLUS if value >= 0 else MINUS
    return f"{sign}{abs(value):02X}"
