from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sampletones_core.configs import Config
from sampletones_shared.types.array import Array


@runtime_checkable
class FrameFeature(Protocol):
    """A frame's spectral reading as the search reads it: one value per bin.

    A frame read by one spectrum method holds that method's histogram, and a frame read by several
    holds their bins stacked (``StackedFeature``). The protocol is checked at runtime, since the
    models holding fragments validate what they hold.
    """

    @property
    def values(self) -> Array:
        """The reading's value in every bin."""


@dataclass(frozen=True)
class Fragment:
    """
    A single analysis frame: its time-domain slice and its spectral feature. A data
    holder — features are produced by a `FeatureExtractor`.
    """

    audio: Array
    feature: FrameFeature
    config: Config
