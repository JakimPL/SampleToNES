from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict


class LinearRampEnvelope(BaseModel):
    """Linear rise from 0 to 1 over the whole time axis, probing the dynamic range."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["linear_ramp"]

    def render(self, time: np.ndarray) -> np.ndarray:
        """
        Render the ramp over the time axis.

        Args:
            time: Sample times in seconds, float64, spanning at least two samples.

        Returns:
            The multiplicative envelope as float64 in [0, 1].
        """
        return time / float(time[-1])
