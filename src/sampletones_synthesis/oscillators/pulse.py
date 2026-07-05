from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones_synthesis.frequency import FrequencySpec, resolve_frequency

DutyCycle = Annotated[float, Field(gt=0.0, lt=1.0)]


class PulseOscillator(BaseModel):
    """Rectangular wave alternating between +1 and -1 at the resolved frequency."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["pulse"]
    frequency: FrequencySpec
    duty_cycle: DutyCycle = Field(description="Fraction of each period spent at +1.")

    def render(
        self,
        time: np.ndarray,
        *,
        generator: np.random.Generator,
    ) -> np.ndarray:
        """
        Render the pulse over the time axis.

        Produces identical output for every generator state.

        Args:
            time: Sample times in seconds, float64.
            generator: Random source shared across a render pass.

        Returns:
            The waveform as float64 taking values in {-1, 1}.
        """
        phase = (resolve_frequency(self.frequency) * time) % 1.0
        return np.where(phase < self.duty_cycle, 1.0, -1.0)
