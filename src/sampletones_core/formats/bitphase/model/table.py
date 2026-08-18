from typing import Tuple

from pydantic import BaseModel, Field

from sampletones_core.formats.bitphase.model.config import BITPHASE_MODEL_CONFIG
from sampletones_core.formats.bitphase.specification.instruments import (
    LOOP_FROM_START,
    MAX_TABLE_ID,
    MIN_TABLE_ID,
)


class BitphaseTable(BaseModel):
    """A list of one value per step, whose meaning the column or effect reading it fixes.

    A pattern's table column reads it as a semitone contour, adding ``rows[position]`` to
    the channel's note and advancing a row every tick, so a table carries the pitch movement
    a reconstruction's arpeggio envelope describes. A speed effect reads it as tick counts,
    advancing a row every pattern line, so a table carries a song's groove.

    Playback returns to ``loop`` once it runs off the end, whichever column drives it.
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
        description="Value applied on each step.",
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
