from typing import Optional

from sampletones.constants.enums import GeneratorName
from sampletones.utils.frequencies import period_to_name, pitch_to_name


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
