from typing import Dict, Tuple

from pydantic import BaseModel, Field

from sampletones_core.formats.bitphase.model.config import BITPHASE_MODEL_CONFIG
from sampletones_core.formats.bitphase.model.pattern import BitphasePattern
from sampletones_core.formats.bitphase.specification.chip import (
    CHIP_TYPE_NES,
    DEFAULT_A4_TUNING,
    DEFAULT_CHIP_VARIANT,
    MAX_INITIAL_SPEED,
    MIN_INITIAL_SPEED,
    ChipVariant,
)


class BitphaseSong(BaseModel):
    """One arrangement of patterns, along with the chip settings it plays under.

    ``interrupt_frequency`` is the engine tick rate in Hz, so it carries the rate a
    reconstruction's envelopes were measured at; ``initial_speed`` is how many of those
    ticks each pattern line lasts.
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
        default=DEFAULT_A4_TUNING,
        description="Concert pitch the tuning table centres on.",
    )
    virtual_channel_map: Dict[int, int] = Field(
        default_factory=dict,
        description="Extra channels folded onto hardware ones.",
    )
