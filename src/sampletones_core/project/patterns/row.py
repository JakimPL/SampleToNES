from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.general import (
    MAX_TRANSPOSE,
    MAX_VOLUME,
    MIN_TRANSPOSE,
)
from sampletones_core.project.instruments.instrument import Instrument


class Row(BaseModel):
    """A single tracker line on one channel.

    All fields are optional: a fully empty row represents a blank line. Effect
    and transpose columns are intentionally deferred to a later step.
    """

    model_config = ConfigDict(frozen=True)

    instrument: Optional[Instrument] = Field(
        default=None,
        description="Referenced channel-slice.",
    )
    transpose: Optional[int] = Field(
        default=None,
        ge=MIN_TRANSPOSE,
        le=MAX_TRANSPOSE,
        description="Note pitch, or None for an empty cell.",
    )
    volume: Optional[int] = Field(
        default=None,
        ge=0,
        le=MAX_VOLUME,
        description="Volume column, or None for an empty cell.",
    )
