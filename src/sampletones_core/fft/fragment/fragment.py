from __future__ import annotations

from dataclasses import dataclass

from sampletones_core.configs import Config
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.types.array import Array


@dataclass(frozen=True)
class Fragment:
    """
    A single analysis frame: its time-domain slice and its spectral feature. A data
    holder — features are produced by a `FeatureExtractor`.
    """

    audio: Array
    feature: Histogram
    config: Config
