from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict


class WhiteNoiseOscillator(BaseModel):
    """Gaussian white noise with unit standard deviation; loudness comes from the layer gain."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["white_noise"]

    def render(
        self,
        time: np.ndarray,
        *,
        generator: np.random.Generator,
    ) -> np.ndarray:
        """
        Draw one noise sample per time-axis sample.

        Args:
            time: Sample times in seconds, float64.
            generator: Random source consumed by the draw.

        Returns:
            The waveform as float64 with unit standard deviation.
        """
        return generator.standard_normal(int(time.shape[0]))
