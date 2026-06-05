from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.general import (
    MAX_PITCH,
    MAX_VOLUME,
    MIN_PITCH,
    MIN_VOLUME,
)
from sampletones_core.project.instruments.subinstrument import SubInstrument


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
    transpose: Optional[int] = Field(
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

    # def __str__(self) -> str:
    #     sample_id = display_id(self.subinstrument.instrument_id if self.subinstrument else None)
    #     volume = display_volume(self.volume)
    #     transpose = display_transpose(self.transpose)
    #     return f"{sample_id} {volume} {transpose}"
