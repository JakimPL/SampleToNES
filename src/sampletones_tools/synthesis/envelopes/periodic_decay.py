from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class PeriodicDecayEnvelope(BaseModel):
    """An exponential decay struck again every period, silent until the first strike."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["periodic_decay"]
    period_seconds: float = Field(gt=0.0, description="Time between strikes in seconds.")
    time_constant_seconds: float = Field(gt=0.0, description="Time constant of each decay in seconds.")
    delay_seconds: float = Field(ge=0.0, description="When the first strike falls, in seconds.")

    def render(self, time: np.ndarray) -> np.ndarray:
        """
        Render the strikes over the time axis.

        Args:
            time: Sample times in seconds, float64.

        Returns:
            The multiplicative envelope as float64 in [0, 1], at full level on every strike.
        """
        elapsed = time - self.delay_seconds
        since_strike = np.mod(elapsed, self.period_seconds)
        return np.where(elapsed >= 0.0, np.exp(-since_strike / self.time_constant_seconds), 0.0)
