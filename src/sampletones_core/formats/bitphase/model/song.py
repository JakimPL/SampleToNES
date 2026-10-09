from typing import Dict, Tuple

from pydantic import BaseModel, Field

from sampletones_core.formats.bitphase.model.config import BITPHASE_MODEL_CONFIG
from sampletones_core.formats.bitphase.model.pattern import BitphasePattern
from sampletones_core.formats.bitphase.specification.chip import (
    CHIP_TYPE_NES,
    DEFAULT_CHIP_VARIANT,
    MAX_A4_TUNING,
    MAX_INITIAL_SPEED,
    MIN_A4_TUNING,
    MIN_INITIAL_SPEED,
    SPEED_CLOCK_TEMPO,
    ChipVariant,
)
from sampletones_core.formats.bitphase.specification.patterns import (
    MAX_PATTERN_LENGTH,
    MIN_PATTERN_LENGTH,
)


class BitphaseSong(BaseModel):
    """One arrangement of patterns, along with the chip settings it plays under.

    ``interrupt_frequency`` is the engine tick rate in Hz, so it carries the rate a
    reconstruction's envelopes were measured at; ``initial_speed`` is how many of those
    ticks each pattern line lasts.

    ``tempo`` stays at the value that lets the speed alone time each line. A tempo above it
    spreads the ticks of a line by FamiTracker's accumulator, so the speed clock keeps every
    line at the tick count the speed effects of the groove state.

    ``a4_tuning_hz`` and ``tuning_table`` state one tuning together. Bitphase builds the table
    again from that frequency and the chip clock when it loads a song, so the two are written in
    step, and the frequency stays within the range the tracker's settings offer.
    """

    model_config = BITPHASE_MODEL_CONFIG

    patterns: Tuple[BitphasePattern, ...] = Field(
        ...,
        description="Every pattern the song holds.",
    )
    tuning_table: Tuple[int, ...] = Field(
        ...,
        description="Channel period for each of the 96 note indices.",
    )
    initial_speed: int = Field(
        ...,
        ge=MIN_INITIAL_SPEED,
        le=MAX_INITIAL_SPEED,
        description="Engine ticks per pattern line.",
    )
    tempo: int = Field(
        default=SPEED_CLOCK_TEMPO,
        description="Tempo spreading a line's ticks, at the value leaving the speed to time each line.",
    )
    default_pattern_length: int = Field(
        ...,
        ge=MIN_PATTERN_LENGTH,
        le=MAX_PATTERN_LENGTH,
        description="Line count a pattern added to the song takes.",
    )
    chip_type: str = Field(
        default=CHIP_TYPE_NES,
        description="Chip the song drives.",
    )
    chip_variant: ChipVariant = Field(
        default=DEFAULT_CHIP_VARIANT,
        description="System whose CPU clock applies.",
    )
    chip_frequency: int = Field(
        ...,
        description="CPU clock in Hz the tuning table was built from.",
    )
    interrupt_frequency: int = Field(
        ...,
        description="Engine tick rate in Hz.",
    )
    a4_tuning_hz: float = Field(
        ...,
        ge=MIN_A4_TUNING,
        le=MAX_A4_TUNING,
        description="Concert pitch the tuning table centers on.",
    )
    virtual_channel_map: Dict[int, int] = Field(
        default_factory=dict,
        description="Extra channels folded onto hardware ones.",
    )
