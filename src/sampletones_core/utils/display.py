from typing import Final, Optional, Union

from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.structures import IdentifiedCollection

DEFAULT_DISPLAY_LENGTH: Final[int] = 2
NOTE_OFF: Final[str] = "~~"


def display_value(
    value: Optional[int],
    *,
    length: int = DEFAULT_DISPLAY_LENGTH,
    hexadecimal: bool = True,
) -> str:
    if value is None:
        return "." * length

    if hexadecimal:
        return f"{value:0{length}X}"

    return f"{value:0{length}d}"


def display_id(value: Optional[int]) -> str:
    return display_value(value, hexadecimal=True)


def display_sample(
    *,
    samples: IdentifiedCollection[Sample],
    sample_id: Optional[str] = None,
) -> str:
    """
    Render a sample reference as its current list position (not its uuid).
    """
    if sample_id is not None and samples.get(sample_id) is not None:
        return display_id(samples.get_index(sample_id))

    return display_id(None)


def display_sample_label(position: int, name: str) -> str:
    """Render an instrument's list label as ``"<hex position>: <name>"`` (e.g. ``"1A: Bass"``)."""
    return f"{display_id(position)}: {name}"


def display_command(
    samples: IdentifiedCollection[Sample],
    command: Optional[Union[Instrument, NoteOff]],
) -> str:
    """Render a row's note-column command: a sample's list position, ``--`` for note-off, or ``..``."""
    match command:
        case NoteOff():
            return NOTE_OFF
        case Instrument():
            return display_sample(samples=samples, sample_id=command.sample_id)
        case None:
            return display_sample(samples=samples, sample_id=None)


def display_volume(value: Optional[int]) -> str:
    return display_value(value, length=1, hexadecimal=True)


def display_transpose(value: Optional[int]) -> str:
    if value is None or value == 0:
        return "..."

    sign = "+" if value > 0 else "-"
    abs_value = abs(value)
    return f"{sign}{abs_value:02X}"
