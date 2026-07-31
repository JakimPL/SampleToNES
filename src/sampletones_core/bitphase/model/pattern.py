from typing import Dict, Optional, Tuple

from pydantic import BaseModel, Field

from sampletones_core.bitphase.model.config import BITPHASE_MODEL_CONFIG
from sampletones_core.bitphase.specification.patterns import (
    EMPTY_OCTAVE,
    FULL_VOLUME,
    MAX_PATTERN_LENGTH,
    MIN_PATTERN_LENGTH,
    NO_INSTRUMENT_CHANGE,
    NO_TABLE_CHANGE,
    NO_VOLUME_CHANGE,
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
    """One effect column of a pattern row."""

    model_config = BITPHASE_MODEL_CONFIG

    effect: int = Field(..., description="Effect identifier.")
    delay: int = Field(default=0, description="Ticks the effect waits before it applies.")
    parameter: int = Field(default=0, description="Effect argument.")
    table_index: Optional[int] = Field(
        default=None,
        description="Table the effect drives, where it takes one.",
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
        ge=NO_VOLUME_CHANGE,
        le=FULL_VOLUME,
        description="Channel volume from this line on.",
    )


class BitphaseChannel(BaseModel):
    """One channel's lines within a pattern."""

    model_config = BITPHASE_MODEL_CONFIG

    rows: Tuple[BitphaseRow, ...] = Field(..., description="One row per pattern line.")
    label: str = Field(..., description="Name of the channel the lines drive.")


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
