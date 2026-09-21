from typing import Dict, Optional, Tuple

from pydantic import BaseModel, Field, computed_field

from sampletones_core.formats.bitphase.model.config import BITPHASE_MODEL_CONFIG
from sampletones_core.formats.bitphase.specification.effects import (
    MIN_EFFECT_COLUMNS,
    NO_EFFECT_TABLE,
)
from sampletones_core.formats.bitphase.specification.patterns import (
    EMPTY_OCTAVE,
    FULL_VOLUME,
    MAX_PATTERN_LENGTH,
    MIN_PATTERN_LENGTH,
    NO_INSTRUMENT_CHANGE,
    NO_TABLE_CHANGE,
    NO_VOLUME_CHANGE,
    VOLUME_OFF,
    NoteName,
)


class NoteCell(BaseModel):
    """The note column of one pattern row, naming a semitone and its octave."""

    model_config = BITPHASE_MODEL_CONFIG

    name: int = Field(
        default=int(NoteName.NONE),
        ge=int(NoteName.NONE),
        le=int(NoteName.B),
        description="Semitone within the octave, or a non-pitched marker.",
    )
    octave: int = Field(
        default=EMPTY_OCTAVE,
        ge=EMPTY_OCTAVE,
        description="Octave the semitone sounds in.",
    )


class EffectCell(BaseModel):
    """One effect column of a pattern row.

    Bitphase reads an effect from a table wherever the cell names an index of zero or
    above, and from the cell's own parameter otherwise, so a parameter-driven effect
    states ``NO_EFFECT_TABLE``.
    """

    model_config = BITPHASE_MODEL_CONFIG

    effect: int = Field(..., description="Effect identifier.")
    delay: int = Field(default=0, description="Ticks the effect waits before it applies.")
    parameter: int = Field(default=0, description="Effect argument.")
    table_index: int = Field(
        default=NO_EFFECT_TABLE,
        ge=NO_EFFECT_TABLE,
        description="Table the effect drives, or NO_EFFECT_TABLE where its parameter drives it.",
    )


class BitphaseRow(BaseModel):
    """A single tracker line on one channel.

    Every column beyond the note carries its own "leave as it is" value, so a blank
    line keeps whatever the channel already plays.
    """

    model_config = BITPHASE_MODEL_CONFIG

    note: NoteCell = Field(default_factory=NoteCell, description="Note column.")
    effects: Tuple[Optional[EffectCell], ...] = Field(
        default=(None,),
        description="One entry per effect column.",
    )
    instrument: int = Field(
        default=NO_INSTRUMENT_CHANGE,
        ge=NO_INSTRUMENT_CHANGE,
        description="Instrument to play from this line on.",
    )
    table: int = Field(default=NO_TABLE_CHANGE, description="Table to attach from this line on.")
    volume: int = Field(
        default=NO_VOLUME_CHANGE,
        ge=VOLUME_OFF,
        le=FULL_VOLUME,
        description="Channel volume from this line on, where VOLUME_OFF silences the channel.",
    )


class BitphaseChannel(BaseModel):
    """One channel's lines within a pattern.

    A channel lays out as many effect columns as its widest line carries, and Bitphase
    holds that width across every pattern the channel appears in.
    """

    model_config = BITPHASE_MODEL_CONFIG

    rows: Tuple[BitphaseRow, ...] = Field(..., description="One row per pattern line.")
    label: str = Field(..., description="Name of the channel the lines drive.")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def effect_column_count(self) -> int:
        """How many effect columns the channel's lines fill."""
        return max((len(row.effects) for row in self.rows), default=MIN_EFFECT_COLUMNS)


class BitphasePattern(BaseModel):
    """One block of tracker lines across every channel.

    ``pattern_rows`` holds the columns a chip declares song-wide rather than per
    channel; the 2A03 declares none, so Bitphase fills the block itself.
    """

    model_config = BITPHASE_MODEL_CONFIG

    id: int = Field(..., ge=0, description="Identifier the pattern order references.")
    length: int = Field(
        ...,
        ge=MIN_PATTERN_LENGTH,
        le=MAX_PATTERN_LENGTH,
        description="Line count every channel of the pattern shares.",
    )
    channels: Tuple[BitphaseChannel, ...] = Field(
        ...,
        description="One entry per chip channel.",
    )
    pattern_rows: Tuple[Dict[str, int], ...] = Field(
        default=(),
        description="Song-wide columns, one entry per line.",
    )
