from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class ExponentialDecayEnvelope(BaseModel):
    """Amplitude decay `exp(-t / tau)` falling from 1 to 1/e at the time constant."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["exponential_decay"]
    time_constant_seconds: float = Field(gt=0.0, description="Time constant of the decay in seconds.")

    def render(self, time: np.ndarray) -> np.ndarray:
        """
        Render the decay over the time axis.

        Args:
            time: Sample times in seconds, float64.

        Returns:
            The multiplicative envelope as float64 in (0, 1].
        """
        return np.exp(-time / self.time_constant_seconds)
