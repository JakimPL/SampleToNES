from dataclasses import dataclass
from typing import Self, Sequence

import numpy as np

from sampletones_core.fft import Fragment

from .contribution import Contribution


@dataclass(frozen=True)
class FrameMix:
    """
    The sound a stem's picks add up to in one frame.

    Picks on different channels sound independently of each other's phase, so their powers add;
    the waveforms they are expected to render add, and so do their variances. A candidate is scored
    against its stem's frame with its own contribution added to this mix, which is what lets the
    cost of adding a channel stand beside the cost of leaving it silent.

    Attributes:
        power: The summed power density per bin.
        expectation: The summed expected waveform.
        variance: The summed per-sample variance.
    """

    power: np.ndarray
    expectation: np.ndarray
    variance: float

    @classmethod
    def empty(cls, target: Fragment) -> Self:
        """The mix of no picks, shaped to the frame it is scored against."""
        silence = Contribution.silence(len(target.feature.values), target.audio.shape[0])
        return cls(power=silence.power, expectation=silence.expectation, variance=silence.variance)

    @classmethod
    def of(cls, target: Fragment, contributions: Sequence[Contribution]) -> Self:
        """The mix of ``contributions``, summed afresh."""
        mix = cls.empty(target)
        for contribution in contributions:
            mix = mix.added(contribution)

        return mix

    def added(self, contribution: Contribution) -> Self:
        """This mix with one more contribution sounding in it."""
        return self.__class__(
            power=self.power + contribution.power,
            expectation=self.expectation + contribution.expectation,
            variance=self.variance + contribution.variance,
        )

    def residual_waveform(self, target: Fragment) -> np.ndarray:
        """What the frame's waveform holds beyond the mix's expected waveform, which a candidate aligns to."""
        residual: np.ndarray = np.asarray(target.audio, dtype=np.float64) - self.expectation
        return residual
