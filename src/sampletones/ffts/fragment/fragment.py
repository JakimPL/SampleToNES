from dataclasses import dataclass, field
from typing import List, Self

import numpy as np

from sampletones.configs import Config

from ..transformations.transformer import FFTTransformer
from ..window.window import Window


@dataclass(frozen=True)
class Fragment:
    audio: np.ndarray
    feature: np.ndarray
    windowed_audio: np.ndarray
    config: Config

    transformer: FFTTransformer = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "transformer", FFTTransformer.from_gamma(self.config.library.transformation_gamma))

    @classmethod
    def create(cls, config: Config, windowed_audio: np.ndarray, window: Window) -> "Fragment":
        assert windowed_audio.shape[0] == window.size, "Audio length must match window size."
        transformer = FFTTransformer.from_gamma(config.library.transformation_gamma)
        feature = transformer.calculate(windowed_audio, window.size)
        return cls(
            audio=window.get_frame_from_window(windowed_audio),
            feature=feature,
            windowed_audio=windowed_audio,
            config=config,
        )

    @classmethod
    def stack(cls, fragments: List[Self]) -> Self:
        if not fragments:
            raise ValueError("The fragments list cannot be empty.")

        first_fragment = fragments[0]
        assert all(
            fragment.config.library == first_fragment.config.library
            and fragment.config.generation.calculation == first_fragment.config.generation.calculation
            for fragment in fragments
        ), "All fragments must have the same config to be concatenated."

        assert all(
            fragment.dimension == first_fragment.dimension for fragment in fragments
        ), "All fragments must have the same number of dimensions to be concatenated."

        concatenated_audio = np.stack([fragment.audio for fragment in fragments])
        concatenated_windowed_audio = np.stack([fragment.windowed_audio for fragment in fragments])
        concatenated_feature = np.stack([fragment.feature for fragment in fragments])

        dimensions = map(
            lambda array: len(array.shape), [concatenated_audio, concatenated_windowed_audio, concatenated_feature]
        )
        assert all(dimension == 2 for dimension in dimensions), "All concatenated arrays must be 2-dimensional."

        return cls(
            audio=concatenated_audio,
            feature=concatenated_feature,
            windowed_audio=concatenated_windowed_audio,
            config=first_fragment.config,
        )

    def __sub__(self, other: Self) -> "Fragment":
        if self.audio.shape != other.audio.shape:
            raise ValueError("Fragments must have the same shape to be subtracted.")

        if (
            self.config.library != other.config.library
            or self.config.generation.calculation != other.config.generation.calculation
        ):
            raise ValueError("Both fragments must have the same config to be subtracted.")

        windowed_audio = self.windowed_audio - other.windowed_audio
        audio = self.audio - other.audio

        if self.config.generation.calculation.fast_difference:
            feature = self.transformer.subtract(self.feature, other.feature)
        else:
            feature = self.transformer.calculate(windowed_audio)

        return Fragment(
            audio=audio,
            feature=feature,
            windowed_audio=windowed_audio,
            config=self.config,
        )

    def __mul__(self, scalar: float) -> "Fragment":
        audio = self.audio * scalar
        windowed_audio = self.windowed_audio * scalar
        feature = self.transformer.multiply(self.feature, scalar)
        return Fragment(
            audio=audio,
            feature=feature,
            windowed_audio=windowed_audio,
            config=self.config,
        )

    @property
    def dimension(self) -> int:
        return len(self.audio.shape)
