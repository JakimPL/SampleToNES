from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Mapping

from sampletones_core.formats.bitphase.specification.instruments import (
    MAX_PULSE_WIDTH,
    MAX_TONE_ADD,
    MAX_VOLUME_OR_RATE,
    MIN_PULSE_WIDTH,
    MIN_TONE_ADD,
    MIN_VOLUME_OR_RATE,
)


class NesMacroField(StrEnum):
    """Instrument field a Bitphase NES macro drives, named as the instrument keys it.

    Bitphase reads each field it offers from the macro carrying that name, and gives a field
    the instrument leaves out a default of its own, so an instrument states the fields whose
    values it decides. These are the three a reconstruction decides.
    """

    VOLUME_OR_RATE = "volumeOrRate"
    PULSE_WIDTH = "pulseWidth"
    TONE_ADD = "toneAdd"


@dataclass(frozen=True)
class MacroFieldSpec:
    """The values a field accepts.

    Attributes:
        minimum: Lowest value the field takes.
        maximum: Highest value the field takes.
    """

    minimum: int
    maximum: int


NES_MACRO_FIELDS: Final[Mapping[NesMacroField, MacroFieldSpec]] = {
    NesMacroField.VOLUME_OR_RATE: MacroFieldSpec(MIN_VOLUME_OR_RATE, MAX_VOLUME_OR_RATE),
    NesMacroField.PULSE_WIDTH: MacroFieldSpec(MIN_PULSE_WIDTH, MAX_PULSE_WIDTH),
    NesMacroField.TONE_ADD: MacroFieldSpec(MIN_TONE_ADD, MAX_TONE_ADD),
}

MIN_MACRO_LENGTH: Final[int] = 1
MAX_MACRO_LENGTH: Final[int] = 512
