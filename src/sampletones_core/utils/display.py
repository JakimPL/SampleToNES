from typing import Final, Optional

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.structures import IdentifiedCollection
from sampletones_core.utils.frequencies import period_to_name, pitch_to_name

DEFAULT_DISPLAY_LENGTH: Final[int] = 2


def display_pitch(value: Optional[int], generator: GeneratorName) -> str:
    if value is None:
        return "..."

    if generator == GeneratorName.NOISE:
        return period_to_name(value)

    return pitch_to_name(value)


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


def display_index(index: Optional[int]) -> str:
    return display_value(index, hexadecimal=False)


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


def display_instrument(
    samples: IdentifiedCollection[Sample],
    instruments: Optional[Instrument],
) -> str:
    sample_id = instruments.sample_id if instruments is not None else None
    return display_sample(samples=samples, sample_id=sample_id)


def display_volume(value: Optional[int]) -> str:
    return display_value(value, length=1, hexadecimal=True)


def display_transpose(value: Optional[int]) -> str:
    if value is None or value == 0:
        return "..."

    sign = "+" if value > 0 else "-"
    abs_value = abs(value)
    return f"{sign}{abs_value:02X}"
