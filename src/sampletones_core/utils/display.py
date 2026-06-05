from typing import Optional

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.subinstrument import SubInstrument
from sampletones_core.structures import IdentifiedCollection
from sampletones_core.utils.frequencies import period_to_name, pitch_to_name


def display_pitch(value: Optional[int], generator: GeneratorName) -> str:
    if value is None:
        return "..."

    if generator == GeneratorName.NOISE:
        return period_to_name(value)

    return pitch_to_name(value)


def display_id(value: Optional[int]) -> str:
    if value is None:
        return ".."

    return f"{value:02X}"


def display_instrument(instruments: IdentifiedCollection[Instrument], instrument_id: Optional[str]) -> str:
    """Render an instrument reference as its current list position (not its uuid).

    Resolution is O(1) via the id-keyed collection, so this is safe to call per
    frame. Missing or absent references render as the empty placeholder.
    """
    if instrument_id is not None and instruments.get(instrument_id) is not None:
        return display_id(instruments.get_index(instrument_id))

    return display_id(None)


def display_subinstrument(
    instruments: IdentifiedCollection[Instrument],
    subinstrument: Optional[SubInstrument],
) -> str:
    instrument_id = subinstrument.instrument_id if subinstrument is not None else None
    return display_instrument(instruments, instrument_id)


def display_volume(value: Optional[int]) -> str:
    if value is None:
        return "."

    return f"{value:01X}"


def display_transpose(value: Optional[int]) -> str:
    if value is None or value == 0:
        return "..."

    sign = "+" if value > 0 else "-"
    abs_value = abs(value)
    return f"{sign}{abs_value:02X}"
