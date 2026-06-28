from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Self

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.array import xp
from sampletones_shared.types.array import Array, get_array_module

from ..transformer import FFTTransformer
from ..window.window import Window


@dataclass(frozen=True)
class Fragment:
    audio: Array
    feature: Histogram
    windowed_audio: Array
    config: Config

    transformer: FFTTransformer = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transformer",
            self._get_transformer(self.config),
        )

    @staticmethod
    def _get_transformer(config: Config) -> FFTTransformer:
        return FFTTransformer.from_gamma(
            config.library.transformation_gamma,
            config.library.sample_rate,
            config.library.spectrum_method,
        )

    @classmethod
    def create(
        cls,
        config: Config,
        windowed_audio: np.ndarray,
        window: Window,
    ) -> Self:
        transformer = cls._get_transformer(config)
        feature = transformer.calculate_feature(windowed_audio, config.library.sample_rate)
        return cls.with_feature(config, windowed_audio, window, feature)

    @classmethod
    def with_feature(
        cls,
        config: Config,
        windowed_audio: np.ndarray,
        window: Window,
        feature: Histogram,
    ) -> Self:
        """
        Build a fragment from a window and an already-computed spectral feature.

        Used when the feature is produced outside the per-window path: the CQT method
        computes every frame's column from one whole-signal transform, so the feature
        cannot be recomputed from this fragment's window alone. Keeps the audio
        slicing in a single place shared with create.
        """
        assert windowed_audio.shape[0] == window.size, "Audio length must match window size"
        return cls(
            audio=window.get_frame_from_window(windowed_audio),
            feature=feature,
            windowed_audio=windowed_audio,
            config=config,
        )

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

    def __sub__(self, other: Self) -> Self:
        if self.audio.shape != other.audio.shape:
            raise ValueError("Fragments must have the same shape to be subtracted")

        if (
            self.config.library != other.config.library
            or self.config.generation.calculation != other.config.generation.calculation
        ):
            raise ValueError("Both fragments must have the same config to be subtracted")

        sample_rate = self.config.library.sample_rate
        windowed_audio = self.windowed_audio - other.windowed_audio
        audio = self.audio - other.audio

        # The CQT feature is produced by a whole-signal transform, so it cannot be
        # recomputed from this residual's local window; subtract in feature space
        # instead (also the behaviour requested by fast_difference).
        use_feature_space = (
            SpectrumMethod(self.config.library.spectrum_method) == SpectrumMethod.CQT
            or self.config.generation.calculation.fast_difference
        )
        if use_feature_space:
            feature = self.transformer.subtract(self.feature, other.feature)
        else:
            feature = self.transformer.calculate_feature(windowed_audio, sample_rate)

        return self.__class__(
            audio=audio,
            feature=feature,
            windowed_audio=windowed_audio,
            config=self.config,
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
