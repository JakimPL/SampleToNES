from dataclasses import dataclass, field
from typing import Iterator, List, Self

import numpy as np
from pydantic import BaseModel, Field

from configs.config import Config as Configuration
from ffts.fft import FFTTransformer
from ffts.window import Window


@dataclass(frozen=True)
class Fragment:
    audio: np.ndarray
    feature: np.ndarray
    windowed_audio: np.ndarray
    config: Configuration

    transformer: FFTTransformer = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "transformer", FFTTransformer.from_gamma(self.config.library.transformation_gamma))

    @classmethod
    def create(cls, config: Configuration, windowed_audio: np.ndarray, window: Window) -> "Fragment":
        assert windowed_audio.shape[0] == window.size, "Audio length must match window size."
        transformer = FFTTransformer.from_gamma(config.library.transformation_gamma)
        feature = transformer.calculate(windowed_audio, window.size)
        return cls(
            audio=window.get_frame_from_window(windowed_audio),
            feature=feature,
            windowed_audio=windowed_audio,
            config=config,
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

    class Config:
        frozen = True
        arbitrary_types_allowed = True


class FragmentedAudio(BaseModel):
    audio: np.ndarray = Field(..., description="Original audio data")
    fragments: List[Fragment] = Field(..., description="List of audio fragments")
    config: Configuration = Field(..., description="Configuration")

    @classmethod
    def create(cls, audio: np.ndarray, config: Configuration, window: Window) -> "FragmentedAudio":
        length = (audio.shape[0] // window.frame_length) * window.frame_length
        audio = audio[:length].copy()
        count = length // window.frame_length
        fragments = [
            Fragment.create(
                config,
                window.get_windowed_frame(audio, fragment_id * window.frame_length),
                window,
            )
            for fragment_id in range(count)
        ]

        return cls(audio=audio, fragments=fragments, config=config)

    def __getitem__(self, index: int) -> Fragment:
        return self.fragments[index]

    def __setitem__(self, index: int, value: Fragment) -> None:
        self.fragments[index] = value

    def __len__(self) -> int:
        return len(self.fragments)

    @property
    def fragments_ids(self) -> List[int]:
        return list(range(len(self.fragments)))

    class Config:
        arbitrary_types_allowed = True
