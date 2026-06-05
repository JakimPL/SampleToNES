from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .subinstrument import Subinstrument


class Row(BaseModel):
    """A single tracker line on one channel.

    All fields are optional: a fully empty row represents a blank line. Effect
    and transpose columns are intentionally deferred to a later step.
    """

    model_config = ConfigDict(frozen=True)

    pitch: Optional[int] = Field(default=None, description="Note pitch, or None for an empty cell.")
    subinstrument: Optional[Subinstrument] = Field(default=None, description="Referenced channel-slice.")
    volume: Optional[int] = Field(default=None, description="Volume column, or None for an empty cell.")
