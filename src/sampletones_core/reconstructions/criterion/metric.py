from dataclasses import dataclass
from typing import Self

from sampletones_core.configs.generation import MetricConfig
from sampletones_core.constants.enums import SpectralDistance


@dataclass(frozen=True)
class SpectralMetric:
    """What the spectral term measures with: the distance family, and the scale it reads bins on.

    The scale states how far under a frame's loudest bin the comparison reaches and how loudly each
    bin counts within that reach, so one frame's quiet detail and another's loud peaks are measured
    the same way.

    Attributes:
        distance: The family the per-bin distance belongs to.
        divergence_beta: The beta of the beta-divergence distance.
        silence_floor: The power a frame whose own bins lie under it is measured from.
        dynamic_range_decibels: How far under the loudest bin the frame's floor sits.
    """

    distance: SpectralDistance
    divergence_beta: float
    silence_floor: float
    dynamic_range_decibels: float

    @classmethod
    def from_config(cls, metric: MetricConfig) -> Self:
        """The metric the configured settings state."""
        return cls(
            distance=SpectralDistance(metric.spectral_distance),
            divergence_beta=float(metric.beta),
            silence_floor=float(metric.silence_floor),
            dynamic_range_decibels=float(metric.dynamic_range_decibels),
        )
