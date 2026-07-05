from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict


class WalkNoiseOscillator(BaseModel):
    """
    Mean-centered random walk normalized to unit peak.

    Integrating white noise concentrates energy at low frequencies, so the
    waveform covers the dark end of the noise-color axis.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["walk_noise"]

    def render(
        self,
        time: np.ndarray,
        *,
        generator: np.random.Generator,
    ) -> np.ndarray:
        """
        Draw and integrate one noise sample per time-axis sample.

        Args:
            time: Sample times in seconds, float64.
            generator: Random source consumed by the draw.

        Returns:
            The waveform as float64 with zero mean and unit peak.
        """
        walk = np.cumsum(generator.standard_normal(int(time.shape[0])))
        walk = walk - np.mean(walk)
        peak = float(np.max(np.abs(walk)))
        return walk / peak
