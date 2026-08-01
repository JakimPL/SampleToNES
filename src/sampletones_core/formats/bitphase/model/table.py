from typing import Tuple

from pydantic import BaseModel, Field

from sampletones_core.formats.bitphase.model.config import BITPHASE_MODEL_CONFIG
from sampletones_core.formats.bitphase.specification.instruments import (
    LOOP_FROM_START,
    MAX_TABLE_ID,
    MIN_TABLE_ID,
)


class BitphaseTable(BaseModel):
    """A per-tick semitone contour a pattern cell attaches to a channel.

    Playback adds ``rows[position]`` to the channel's note every tick, advancing one
    row per tick, so a table carries the pitch movement a reconstruction's arpeggio
    envelope describes.
    """

    model_config = BITPHASE_MODEL_CONFIG

    id: int = Field(
        ...,
        ge=MIN_TABLE_ID,
        le=MAX_TABLE_ID,
        description="Identifier a pattern's table column names.",
    )
    rows: Tuple[int, ...] = Field(
        ...,
        description="Semitone offset applied on each tick.",
    )
    loop: int = Field(
        default=LOOP_FROM_START,
        ge=0,
        description="Row playback returns to after the last row.",
    )
    name: str = Field(
        ...,
        description="Name shown in the table list.",
    )
