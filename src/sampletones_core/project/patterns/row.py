from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.general import (
    MAX_PITCH,
    MAX_VOLUME,
    MIN_PITCH,
    MIN_VOLUME,
)

from .subinstrument import SubInstrument


class Row(BaseModel):
    """A single tracker line on one channel.

    All fields are optional: a fully empty row represents a blank line. Effect
    and transpose columns are intentionally deferred to a later step.
    """

    model_config = ConfigDict(frozen=True)

    subinstrument: Optional[SubInstrument] = Field(
        default=None,
        description="Referenced channel-slice.",
    )
    pitch: Optional[int] = Field(
        default=None,
        ge=MIN_PITCH,
        le=MAX_PITCH,
        description="Note pitch, or None for an empty cell.",
    )
    volume: Optional[int] = Field(
        default=None,
        ge=MIN_VOLUME,
        le=MAX_VOLUME,
        description="Volume column, or None for an empty cell.",
    )
