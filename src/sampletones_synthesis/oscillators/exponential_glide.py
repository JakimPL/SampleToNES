from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones_synthesis.frequency import FrequencySpec, resolve_frequency


class ExponentialGlideOscillator(BaseModel):
    """
    Sine whose frequency decays exponentially from the start toward the end frequency.

    The instantaneous frequency follows
    `f(t) = f_end + (f_start - f_end) * exp(-t / tau)` — the pitch drop of a
    percussive kick. The frequency profile is integrated into phase in closed
    form, so every sample carries the exact analytic phase.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["exponential_glide"]
    frequency_start: FrequencySpec
    frequency_end: FrequencySpec
    time_constant_seconds: float = Field(
        gt=0.0,
        description="Time constant of the glide toward the end frequency.",
    )

    def render(
        self,
        time: np.ndarray,
        *,
        generator: np.random.Generator,
    ) -> np.ndarray:
        """
        Render the glide over the time axis.

        Produces identical output for every generator state.

        Args:
            time: Sample times in seconds, float64.
            generator: Random source shared across a render pass.

        Returns:
            The waveform as float64 in [-1, 1].
        """
        frequency_start = resolve_frequency(self.frequency_start)
        frequency_end = resolve_frequency(self.frequency_end)
        glide = (
            self.time_constant_seconds
            * (frequency_start - frequency_end)
            * np.expm1(-time / self.time_constant_seconds)
        )
        phase = 2.0 * np.pi * (frequency_end * time - glide)
        return np.sin(phase)
