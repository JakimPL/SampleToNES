from dataclasses import dataclass
from typing import Self

import numpy as np

from sampletones_core.fft import Fragment


@dataclass(frozen=True)
class Contribution:
    """
    What one channel's candidate adds to a frame it is scored in.

    The channel settles the phase it renders at after the matching, so the power a candidate adds
    is its power averaged over the phases a frame starts on. The waveform it adds depends on what
    its frames have in common: a candidate whose frames repeat one shape adds its rendering aligned
    to what the frame still holds, and a candidate whose frames show different stretches of a
    sequence adds its mean level, with its spread about that mean as the variance.

    Attributes:
        power: The candidate's power density per bin, read at unit drive.
        expectation: The waveform the candidate is expected to render over the frame.
        variance: The per-sample variance about that waveform.
        sounding: Whether the candidate sounds a note, which a frame's cost charges the channel for.
    """

    power: np.ndarray
    expectation: np.ndarray
    variance: float
    sounding: bool

    @classmethod
    def silence(cls, bins: int, frame_length: int) -> Self:
        """The contribution of a channel sounding nothing."""
        return cls(
            power=np.zeros(bins, dtype=np.float64),
            expectation=np.zeros(frame_length, dtype=np.float64),
            variance=0.0,
            sounding=False,
        )

    @classmethod
    def silence_of(cls, fragment: Fragment) -> Self:
        """The contribution of a channel sounding nothing in ``fragment``, over its bins and its samples."""
        return cls.silence(len(fragment.feature.values), fragment.audio.shape[0])
