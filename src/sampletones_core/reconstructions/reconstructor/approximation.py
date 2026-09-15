from dataclasses import dataclass
from typing import Protocol

from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.array import xp

from ..criterion import Criterion


class Approximation(Protocol):
    """What a candidate contributes to a frame it is scored on.

    A candidate costs something against the target over time and leaves part of the target for the
    channels still to answer, and how it does both depends on what its frames have in common, so
    the matching asks the approximation for each.
    """

    def temporal_loss(self, target: Fragment, criterion: Criterion) -> xp.ndarray:
        """The temporal term of the candidate's cost against ``target``, as a stack of one."""

    def residual(self, target: Fragment, extractor: FeatureExtractor) -> Fragment:
        """What remains of ``target`` for the channels still to answer."""


@dataclass(frozen=True)
class WaveformApproximation:
    """A candidate measured by the waveform it renders.

    A candidate whose frames repeat one waveform shape renders it at whatever phase the frame
    starts on, so the rendering found against the target stands for every frame it plays, and
    the target keeps what that rendering leaves of it.
    """

    rendering: Fragment

    def temporal_loss(self, target: Fragment, criterion: Criterion) -> xp.ndarray:
        return criterion.temporal_loss(
            xp.asarray(target.audio),
            xp.asarray(self.rendering.audio),
        )

    def residual(self, target: Fragment, extractor: FeatureExtractor) -> Fragment:
        return extractor.subtract(target, self.rendering)


@dataclass(frozen=True)
class ExpectedApproximation:
    """A candidate measured by what it contributes on average over the phases a frame starts on.

    A candidate whose frames show different stretches of a pseudo-random sequence plays whichever
    stretch the channel's register has reached when the frame is rendered, which the decoded path
    settles after the matching. Its temporal term is the loss expected over every phase, and the target keeps what
    an uncorrelated contribution leaves of it: its level beyond the candidate's mean, and its power
    beyond the candidate's power.

    Attributes:
        feature: The candidate's phase-averaged feature at unit drive.
        mean: The mean level of the candidate's sample at unit drive.
        variance: The variance of the candidate's sample at unit drive.
        drive: The amplitude the candidate plays at.
    """

    feature: Histogram
    mean: float
    variance: float
    drive: float

    def temporal_loss(self, target: Fragment, criterion: Criterion) -> xp.ndarray:
        return criterion.expected_temporal_loss(
            xp.asarray(target.audio),
            self.drive * self.mean,
            self.drive**2 * self.variance,
        )

    def residual(self, target: Fragment, extractor: FeatureExtractor) -> Fragment:
        return extractor.remove_expectation(
            target,
            self.drive * self.mean,
            self.feature,
            self.drive**2,
        )
