from typing import Tuple

from pydantic import BaseModel, Field

from sampletones_core.bitphase.model.config import BITPHASE_MODEL_CONFIG
from sampletones_core.bitphase.specification.chip import CHIP_TYPE_NES
from sampletones_core.bitphase.specification.instruments import (
    ABSOLUTE_TONE,
    CONSTANT_VOLUME,
    KEEP_PHASE,
    LOOP_FROM_START,
    MAX_PULSE_WIDTH,
    MAX_SOUND_LENGTH,
    MAX_SWEEP_RATE,
    MAX_SWEEP_SHIFT,
    MAX_TONE_ADD,
    MAX_VOLUME_OR_RATE,
    MIN_PULSE_WIDTH,
    MIN_SOUND_LENGTH,
    MIN_SWEEP_RATE,
    MIN_SWEEP_SHIFT,
    MIN_TONE_ADD,
    MIN_VOLUME_OR_RATE,
    NO_SWEEP,
    NO_SWEEP_RATE,
    NO_SWEEP_SHIFT,
    NO_TONE_OFFSET,
    SUSTAINED_SOUND_LENGTH,
)


class NesInstrumentRow(BaseModel):
    """One tick of a Bitphase NES instrument.

    An instrument advances one row per engine tick, so a row carries every register
    value the channel takes for that tick. ``pulse_width`` selects the duty on a square
    channel and the LFSR mode on the noise channel; ``volume_or_rate`` is a literal
    volume while ``envelope`` stays off. The remaining fields hold the settings a
    reconstruction leaves alone: the note sustains, the pitch comes from the tuning
    table, and the hardware sweep stays disabled.
    """

    model_config = BITPHASE_MODEL_CONFIG

    pulse_width: int = Field(
        ...,
        ge=MIN_PULSE_WIDTH,
        le=MAX_PULSE_WIDTH,
        description="Square duty cycle, or the noise channel's LFSR mode.",
    )
    volume_or_rate: int = Field(
        ...,
        ge=MIN_VOLUME_OR_RATE,
        le=MAX_VOLUME_OR_RATE,
        description="Channel volume while the hardware envelope stays off.",
    )
    retrigger: bool = Field(
        default=KEEP_PHASE,
        description="Restarts the waveform phase this tick.",
    )
    sound_length: int = Field(
        default=SUSTAINED_SOUND_LENGTH,
        ge=MIN_SOUND_LENGTH,
        le=MAX_SOUND_LENGTH,
        description="Length counter in ticks; zero holds the note for as long as the envelope runs.",
    )
    envelope: bool = Field(
        default=CONSTANT_VOLUME,
        description="Reads volume_or_rate as a decay rate.",
    )
    tone_add: int = Field(
        default=NO_TONE_OFFSET,
        ge=MIN_TONE_ADD,
        le=MAX_TONE_ADD,
        description="Offset added to the tuning-table period on a square or triangle channel.",
    )
    tone_accumulation: bool = Field(
        default=ABSOLUTE_TONE,
        description="Sums tone_add across ticks.",
    )
    sweep: bool = Field(
        default=NO_SWEEP,
        description="Enables the square channel's sweep unit.",
    )
    sweep_rate: int = Field(
        default=NO_SWEEP_RATE,
        ge=MIN_SWEEP_RATE,
        le=MAX_SWEEP_RATE,
    )
    sweep_shift: int = Field(
        default=NO_SWEEP_SHIFT,
        ge=MIN_SWEEP_SHIFT,
        le=MAX_SWEEP_SHIFT,
    )


class BitphaseInstrument(BaseModel):
    """A named row list one pattern cell triggers, held in a project's instrument list.

    ``id`` is the base-36 text a pattern's instrument column matches on, and ``loop``
    is the row playback returns to once it runs off the end.
    """

    model_config = BITPHASE_MODEL_CONFIG

    id: str = Field(
        ...,
        description="Base-36 identifier a pattern row references.",
    )
    chip_type: str = Field(
        default=CHIP_TYPE_NES,
        description="Chip whose row layout the instrument uses.",
    )
    rows: Tuple[NesInstrumentRow, ...] = Field(
        ...,
        description="One row per engine tick.",
    )
    loop: int = Field(
        default=LOOP_FROM_START,
        ge=0,
        description="Row playback returns to after the last row.",
    )
    name: str = Field(
        ...,
        description="Name shown in the instrument list.",
    )


class BitphaseInstrumentPreset(BaseModel):
    """A single instrument as Bitphase's instruments panel loads and saves it.

    The panel writes the loaded rows into the instrument slot the user has selected,
    which supplies the id and leaves this file carrying the rows alone.
    """

    model_config = BITPHASE_MODEL_CONFIG

    chip_type: str = Field(
        default=CHIP_TYPE_NES,
        description="Chip whose row layout the preset uses.",
    )
    name: str = Field(
        ...,
        description="Name the preset offers for the instrument.",
    )
    loop: int = Field(
        default=LOOP_FROM_START,
        ge=0,
        description="Row playback returns to after the last row.",
    )
    rows: Tuple[NesInstrumentRow, ...] = Field(
        ...,
        description="One row per engine tick.",
    )
