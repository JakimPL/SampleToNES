from typing import Literal, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator


class GateEnvelope(BaseModel):
    """Full level from the start of the gate until its end, silence outside it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["gate"]
    start_seconds: float = Field(ge=0.0, description="When the gate opens, in seconds.")
    end_seconds: float = Field(gt=0.0, description="When the gate closes, in seconds.")

    @model_validator(mode="after")
    def _validate_span(self) -> Self:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("A gate closes after it opens")

        return self

    def render(self, time: np.ndarray) -> np.ndarray:
        """
        Render the gate over the time axis.

        Args:
            time: Sample times in seconds, float64.

        Returns:
            The multiplicative envelope as float64, 1 inside the gate and 0 outside it.
        """
        return ((time >= self.start_seconds) & (time < self.end_seconds)).astype(np.float64)
