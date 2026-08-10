from typing import Tuple

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones_synthesis.envelopes.types import EnvelopeUnion
from sampletones_synthesis.oscillators.types import OscillatorUnion


class Layer(BaseModel):
    """
    One voice component: a unit-scale oscillator shaped by multiplicative envelopes.

    The gain scales the oscillator-envelope product before layers are summed,
    so relative loudness between layers is explicit in the configuration.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    oscillator: OscillatorUnion
    envelopes: Tuple[EnvelopeUnion, ...] = Field(
        ...,
        description="Multiplicative amplitude shapes applied in order.",
    )
    gain: float = Field(
        gt=0.0,
        description="Scale of the unit-level oscillator-envelope product.",
    )

    def render(
        self,
        time: np.ndarray,
        *,
        generator: np.random.Generator,
    ) -> np.ndarray:
        """
        Render the layer over the time axis.

        Args:
            time: Sample times in seconds, float64.
            generator: Random source consumed by stochastic oscillators.

        Returns:
            The scaled waveform as float64.
        """
        audio = self.oscillator.render(time, generator=generator)
        for envelope in self.envelopes:
            audio = audio * envelope.render(time)

        return self.gain * audio
