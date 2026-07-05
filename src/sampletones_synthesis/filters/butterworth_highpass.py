from typing import Final, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from scipy.signal import butter, sosfilt

FILTER_TYPE: Final[str] = "highpass"


class ButterworthHighpassFilter(BaseModel):
    """Butterworth high-pass shaping attenuating content below the cutoff."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["butterworth_highpass"]
    cutoff_hz: float = Field(gt=0.0, description="Cutoff frequency in Hz.")
    order: int = Field(ge=1, description="Filter order; higher orders roll off more steeply.")

    def apply(self, audio: np.ndarray, *, sample_rate: int) -> np.ndarray:
        """
        Filter a rendered waveform.

        Args:
            audio: Waveform to shape, float64.
            sample_rate: Sampling rate of the waveform in Hz.

        Returns:
            The filtered waveform as float64.
        """
        sections = butter(
            self.order,
            self.cutoff_hz,
            btype=FILTER_TYPE,
            fs=sample_rate,
            output="sos",
        )
        filtered: np.ndarray = sosfilt(sections, audio)
        return filtered
