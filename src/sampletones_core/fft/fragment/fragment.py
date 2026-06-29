from __future__ import annotations

from dataclasses import dataclass
from typing import List, Self

from sampletones_core.configs import Config
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.array import xp
from sampletones_shared.types.array import Array, get_array_module


@dataclass(frozen=True)
class Fragment:
    """
    A single analysis frame: its central time-domain slice, the larger analysis
    window it was taken from, and its spectral feature. A data holder — features and
    residuals are produced by a `FeatureExtractor`, not here.
    """

    audio: Array
    feature: Histogram
    windowed_audio: Array
    config: Config

    @classmethod
    def stack(cls, fragments: List[Self]) -> Self:
        if not fragments:
            raise ValueError("The fragments list cannot be empty")

        first_fragment = fragments[0]
        assert all(
            fragment.config.library == first_fragment.config.library
            and fragment.config.generation.calculation == first_fragment.config.generation.calculation
            for fragment in fragments
        ), "All fragments must have the same config to be concatenated"

        assert all(
            fragment.ndim == first_fragment.ndim for fragment in fragments
        ), "All fragments must have the same number of dimensions to be concatenated"

        module = get_array_module(first_fragment.audio)
        concatenated_audio = module.stack([fragment.audio for fragment in fragments])
        concatenated_windowed_audio = module.stack([fragment.windowed_audio for fragment in fragments])
        concatenated_feature = module.stack([fragment.feature.values for fragment in fragments])

        dimensions = map(
            lambda array: array.ndim,
            [
                concatenated_audio,
                concatenated_windowed_audio,
                concatenated_feature,
            ],
        )
        assert all(ndim == 2 for ndim in dimensions), "All concatenated arrays must be 2-dimensional"

        feature: Histogram = Histogram(
            edges=first_fragment.feature.edges,
            values=concatenated_feature,
        )

        return cls(
            audio=concatenated_audio,
            feature=feature,
            windowed_audio=concatenated_windowed_audio,
            config=first_fragment.config,
        )

    def __mul__(self, scalar: float) -> Self:
        audio = self.audio * scalar
        windowed_audio = self.windowed_audio * scalar
        feature = self.feature * scalar
        return self.__class__(
            audio=audio,
            feature=feature,
            windowed_audio=windowed_audio,
            config=self.config,
        )

    def to_cupy(self) -> Self:
        audio = xp.asarray(self.audio)
        windowed_audio = xp.asarray(self.windowed_audio)
        feature = self.feature.to_cupy()
        return self.__class__(
            audio=audio,
            feature=feature,
            windowed_audio=windowed_audio,
            config=self.config,
        )

    @property
    def ndim(self) -> int:
        return int(self.audio.ndim)
