from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones_synthesis.frequency import FrequencySpec, resolve_frequency


class GeometricSweepOscillator(BaseModel):
    """
    Sine whose frequency glides geometrically between the endpoint frequencies.

    The instantaneous frequency follows `f(t) = f_start * (f_end / f_start)^(t / T)`
    over the time-axis span `T` — a straight line in pitch. The frequency profile
    is integrated into phase in closed form, so every sample carries the exact
    analytic phase.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["geometric_sweep"]
    frequency_start: FrequencySpec
    frequency_end: FrequencySpec

    def render(
        self,
        time: np.ndarray,
        *,
        generator: np.random.Generator,  # pylint: disable=unused-argument
    ) -> np.ndarray:
        """
        Render the sweep over the time axis.

        Produces identical output for every generator state. Equal endpoint
        frequencies yield a steady tone (the analytic limit of the sweep).

        Args:
            time: Sample times in seconds, float64, spanning at least two samples.
            generator: Random source shared across a render pass.

        Returns:
            The waveform as float64 in [-1, 1].
        """
        frequency_start = resolve_frequency(self.frequency_start)
        frequency_end = resolve_frequency(self.frequency_end)
        span = float(time[-1])
        ratio = frequency_end / frequency_start
        if ratio == 1.0:
            return np.sin(2.0 * np.pi * frequency_start * time)

        log_ratio = float(np.log(ratio))
        phase = 2.0 * np.pi * frequency_start * span * np.expm1(time / span * log_ratio) / log_ratio
        waveform: np.ndarray = np.sin(phase)
        return waveform
