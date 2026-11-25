from typing import Final, List, Sequence, Tuple

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones_tools.synthesis.filters.types import FilterUnion

from .layer import Layer

MINIMUM_RENDER_SAMPLES: Final[int] = 2


class Voice(BaseModel):
    """
    A complete synthesized sound: layered oscillators summed and filtered.

    Layers render independently over one shared time axis and sum in float64;
    filters then shape the sum in order. A caller may render the layers alone
    and mix them as the voice does, to hold the parts of one rendered sound.
    The output is raw unit-scale audio —
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
        Render the voice at a sample rate: its layers, mixed.

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
        layers = self.render_layers(sample_rate=sample_rate, generator=generator)
        return self.mix_layers(layers, sample_rate=sample_rate)

    def render_layers(
        self,
        *,
        sample_rate: int,
        generator: np.random.Generator,
    ) -> List[np.ndarray]:
        """
        Render each layer at a sample rate, over the voice's one time axis.

        Layers draw from the generator in declaration order, as ``render`` draws
        them, so a caller holding the layers holds the parts of the very sound
        ``render`` makes from the same generator.

        Args:
            sample_rate: Sampling rate in Hz.
            generator: Random source consumed by stochastic oscillators.

        Returns:
            Each layer's waveform as float64, in declaration order.

        Raises:
            ValueError: If the duration yields fewer than two samples.
        """
        time = self._timeline(sample_rate)
        return [layer.render(time, generator=generator) for layer in self.layers]

    def mix_layers(self, layers: Sequence[np.ndarray], *, sample_rate: int) -> np.ndarray:
        """
        Mix rendered layers as the voice mixes its own: their sum in float64, shaped by the filters in order.

        Every layer of the voice mixes into the voice itself, and some of them
        into the part of the voice they play. The filters are linear, so the
        parts of one voice add up to the whole.

        Args:
            layers: Rendered layers of the voice, each spanning its time axis.
            sample_rate: Sampling rate in Hz.

        Returns:
            The mixed waveform as float64.

        Raises:
            ValueError: If the duration yields fewer than two samples.
        """
        audio = np.zeros(self._length(sample_rate), dtype=np.float64)
        for layer in layers:
            audio = audio + layer

        for audio_filter in self.filters:
            audio = audio_filter.apply(audio, sample_rate=sample_rate)

        return audio

    def _timeline(self, sample_rate: int) -> np.ndarray:
        """Sample times in seconds for the configured duration."""
        return np.arange(self._length(sample_rate), dtype=np.float64) / sample_rate

    def _length(self, sample_rate: int) -> int:
        """
        How many samples the configured duration spans.

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

        return length
