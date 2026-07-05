from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class LinearAttackEnvelope(BaseModel):
    """Linear rise from 0 to full level over the attack, holding 1 afterwards."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["linear_attack"]
    attack_seconds: float = Field(gt=0.0, description="Duration of the rise in seconds.")

    def render(self, time: np.ndarray) -> np.ndarray:
        """
        Render the attack over the time axis.

        Args:
            time: Sample times in seconds, float64.

        Returns:
            The multiplicative envelope as float64 in [0, 1].
        """
        return np.minimum(time / self.attack_seconds, 1.0)
