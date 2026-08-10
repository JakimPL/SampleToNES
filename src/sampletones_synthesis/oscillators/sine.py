from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones_synthesis.frequency import FrequencySpec, resolve_frequency


class SineOscillator(BaseModel):
    """Steady sine tone at the resolved frequency, unit amplitude."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["sine"]
    frequency: FrequencySpec

    def render(
        self,
        time: np.ndarray,
        *,
        generator: np.random.Generator,  # pylint: disable=unused-argument
    ) -> np.ndarray:
        """
        Render the sine over the time axis.

        Produces identical output for every generator state.

        Args:
            time: Sample times in seconds, float64.
            generator: Random source shared across a render pass.

        Returns:
            The waveform as float64 in [-1, 1].
        """
        return np.sin(2.0 * np.pi * resolve_frequency(self.frequency) * time)
