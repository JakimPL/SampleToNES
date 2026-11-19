from typing import Final, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones_tools.synthesis.frequency import FrequencySpec, resolve_frequency

CENTS_PER_OCTAVE: Final[float] = 1200.0


class VibratoOscillator(BaseModel):
    """A harmonic of a tone whose pitch swings sinusoidally around its frequency, unit amplitude.

    The fundamental swings ``depth_cents`` above and below ``frequency`` ``rate_hertz`` times a
    second, and the oscillator sounds its ``harmonic``-th partial, so harmonics of one vibrato tone
    layered together keep their phases locked.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["vibrato"]
    frequency: FrequencySpec
    rate_hertz: float = Field(gt=0.0, description="How many times a second the pitch swings.")
    depth_cents: float = Field(ge=0.0, description="How far the pitch swings each way, in cents.")
    harmonic: int = Field(ge=1, description="The partial of the swinging fundamental sounded.")

    def frequency_at(self, time: np.ndarray) -> np.ndarray:
        """The fundamental's instantaneous frequency in Hz at each time."""
        swing = self.depth_cents / CENTS_PER_OCTAVE * np.sin(2.0 * np.pi * self.rate_hertz * time)
        return resolve_frequency(self.frequency) * np.power(2.0, swing)

    def render(
        self,
        time: np.ndarray,
        *,
        generator: np.random.Generator,  # pylint: disable=unused-argument
    ) -> np.ndarray:
        """
        Render the swinging harmonic over the time axis.

        Produces identical output for every generator state.

        Args:
            time: Sample times in seconds, float64, evenly spaced.
            generator: Random source shared across a render pass.

        Returns:
            The waveform as float64 in [-1, 1].
        """
        if time.size < 2:
            return np.zeros_like(time)

        step = float(time[1] - time[0])
        frequency = self.frequency_at(time)
        phase = 2.0 * np.pi * step * (np.cumsum(frequency) - frequency[0])
        return np.asarray(np.sin(self.harmonic * phase), dtype=np.float64)
