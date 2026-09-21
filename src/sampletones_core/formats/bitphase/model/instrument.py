from __future__ import annotations

from typing import Dict, Tuple

from pydantic import BaseModel, Field, model_validator

from sampletones_core.formats.bitphase.model.config import BITPHASE_MODEL_CONFIG
from sampletones_core.formats.bitphase.specification.chip import CHIP_TYPE_NES
from sampletones_core.formats.bitphase.specification.instruments import LOOP_FROM_START
from sampletones_core.formats.bitphase.specification.macros import (
    MAX_MACRO_LENGTH,
    MIN_MACRO_LENGTH,
    NES_MACRO_FIELDS,
    NesMacroField,
)


class InstrumentMacro(BaseModel):
    """One field of an instrument, read a value per engine tick.

    Every field advances on a counter of its own, so a macro carries the length and the
    repeat point that field alone asks for. ``loop`` indexes the values, and playback
    circles from it once the values run out — which makes the whole macro circle where it
    stands at the first value, and the last value hold where it stands at the last.
    """

    model_config = BITPHASE_MODEL_CONFIG

    values: Tuple[int, ...] = Field(
        ...,
        min_length=MIN_MACRO_LENGTH,
        max_length=MAX_MACRO_LENGTH,
        description="Value the field takes on each tick.",
    )
    loop: int = Field(
        default=LOOP_FROM_START,
        ge=0,
        description="Index among the values playback circles from.",
    )

    @model_validator(mode="after")
    def _check_loop(self) -> InstrumentMacro:
        if self.loop >= len(self.values):
            raise ValueError(f"loop {self.loop} stands past the {len(self.values)} values written")

        return self


class MacroInstrument(BaseModel):
    """The fields every stored Bitphase instrument carries.

    An instrument states a macro for each field whose values it decides, and Bitphase reads
    every other field it offers at that field's own default.
    """

    model_config = BITPHASE_MODEL_CONFIG

    chip_type: str = Field(
        default=CHIP_TYPE_NES,
        description="Chip whose fields the macros drive.",
    )
    name: str = Field(
        ...,
        description="Name shown in the instrument list.",
    )
    macros: Dict[NesMacroField, InstrumentMacro] = Field(
        ...,
        description="One macro per field the instrument decides.",
    )

    @model_validator(mode="after")
    def _check_values(self) -> MacroInstrument:
        for field, macro in self.macros.items():
            spec = NES_MACRO_FIELDS[field]
            for value in macro.values:
                if not spec.minimum <= value <= spec.maximum:
                    raise ValueError(f"{field} holds {value}, outside the {spec.minimum}..{spec.maximum} it takes")

        return self


class BitphaseInstrument(MacroInstrument):
    """A named instrument one pattern cell triggers, held in a project's instrument list.

    ``id`` is the base-36 text a pattern's instrument column matches on.
    """

    id: str = Field(
        ...,
        description="Base-36 identifier a pattern row references.",
    )


class BitphaseInstrumentPreset(MacroInstrument):
    """A single instrument as Bitphase's instruments panel loads and saves it.

    The panel writes the loaded macros into the instrument slot the user has selected,
    which supplies the id and the chip and leaves this file carrying the macros alone.
    """
