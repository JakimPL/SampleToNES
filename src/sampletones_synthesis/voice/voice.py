from typing import Final, Tuple

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones_synthesis.filters.types import FilterUnion

from .layer import Layer

MINIMUM_RENDER_SAMPLES: Final[int] = 2


class Voice(BaseModel):
    """
    A complete synthesized sound: layered oscillators summed and filtered.

    Layers render independently over one shared time axis and sum in float64;
    filters then shape the sum in order. The output is raw unit-scale audio —
    loudness policy (peak normalization or amplitude scaling) belongs to the
    caller, so one voice definition serves every loudness convention.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    duration_seconds: float = Field(gt=0.0, description="Length of the rendered sound in seconds.")
    layers: Tuple[Layer, ...] = Field(min_length=1, description="Components summed into the voice.")
    filters: Tuple[FilterUnion, ...] = Field(description="Spectral shaping applied to the layer sum, in order.")

    def render(
        self,
        *,
        sample_rate: int,
        generator: np.random.Generator,
    ) -> np.ndarray:
        """
        Render the voice at a sample rate.

        Layers draw from the generator in declaration order, so a fixed seed
        reproduces the voice exactly.

        Args:
            sample_rate: Sampling rate in Hz.
            generator: Random source consumed by stochastic oscillators.

        Returns:
            The rendered waveform as float64.

        Raises:
            ValueError: If the duration yields fewer than two samples.
        """
        time = self._timeline(sample_rate)
        audio = np.zeros(time.shape[0], dtype=np.float64)
        for layer in self.layers:
            audio = audio + layer.render(time, generator=generator)

        for audio_filter in self.filters:
            audio = audio_filter.apply(audio, sample_rate=sample_rate)

        return audio

    def _timeline(self, sample_rate: int) -> np.ndarray:
        """
        Sample times in seconds for the configured duration.

        Raises:
            ValueError: If the duration yields fewer than two samples, the
                minimum for span-dependent components (ramps, sweeps, walks).
        """
        length = round(self.duration_seconds * sample_rate)
        if length < MINIMUM_RENDER_SAMPLES:
            raise ValueError(
                f"Voice of {self.duration_seconds}s at {sample_rate}Hz yields {length} samples; "
                f"at least {MINIMUM_RENDER_SAMPLES} are required"
            )

        return np.arange(length, dtype=np.float64) / sample_rate
