from dataclasses import dataclass, field
from typing import Iterator, List, Self

import numpy as np
from pydantic import BaseModel, Field

from configs.calculation import CalculationConfig
from ffts.fft import FFTTransformer
from ffts.window import Window


@dataclass(frozen=True)
class Fragment:
    audio: np.ndarray
    feature: np.ndarray
    windowed_audio: np.ndarray
    calculation_config: CalculationConfig

    transformer: FFTTransformer = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "transformer", FFTTransformer.from_name(self.calculation_config.transformation))

    @classmethod
    def create(cls, calculation_config: CalculationConfig, windowed_audio: np.ndarray, window: Window) -> "Fragment":
        assert windowed_audio.shape[0] == window.size, "Audio length must match window size."
        transformer = FFTTransformer.from_name(calculation_config.transformation)
        feature = transformer.calculate_log_arfft(windowed_audio, window.size)
        return cls(
            audio=window.get_frame_from_window(windowed_audio),
            feature=feature,
            windowed_audio=windowed_audio,
            calculation_config=calculation_config,
        )

    def __sub__(self, other: Self) -> "Fragment":
        if self.audio.shape != other.audio.shape:
            raise ValueError("Fragments must have the same shape to be subtracted.")

        if self.calculation_config != other.calculation_config:
            raise ValueError("Both fragments must have the same calculation config to be subtracted.")

        windowed_audio = self.windowed_audio - other.windowed_audio
        audio = self.audio - other.audio

        if self.calculation_config.fast_log_arfft:
            feature = self.transformer.log_arfft_subtract(self.feature, other.feature)
        else:
            feature = self.transformer.calculate_log_arfft(windowed_audio)

        return Fragment(
            audio=audio,
            feature=feature,
            windowed_audio=windowed_audio,
            calculation_config=self.calculation_config,
        )

    def __mul__(self, scalar: float) -> "Fragment":
        audio = self.audio * scalar
        windowed_audio = self.windowed_audio * scalar
        feature = self.transformer.log_arfft_multiply(self.feature, scalar)
        return Fragment(
            audio=audio,
            feature=feature,
            windowed_audio=windowed_audio,
            calculation_config=self.calculation_config,
        )

    class Config:
        frozen = True
        arbitrary_types_allowed = True


class FragmentedAudio(BaseModel):
    audio: np.ndarray = Field(..., description="Original audio data")
    fragments: list[Fragment] = Field(..., description="List of audio fragments")
    calculation_config: CalculationConfig = Field(..., description="Calculation configuration")

    @classmethod
    def create(cls, calculation_config: CalculationConfig, audio: np.ndarray, window: Window) -> "FragmentedAudio":
        length = (audio.shape[0] // window.frame_length) * window.frame_length
        audio = audio[:length].copy()
        count = length // window.frame_length
        fragments = [
            Fragment.create(
                calculation_config,
                window.get_windowed_frame(audio, fragment_id * window.frame_length),
                window,
            )
            for fragment_id in range(count)
        ]

        return cls(audio=audio, fragments=fragments, calculation_config=calculation_config)

    def __getitem__(self, index: int) -> Fragment:
        return self.fragments[index]

    def __setitem__(self, index: int, value: Fragment) -> None:
        self.fragments[index] = value

    def __len__(self) -> int:
        return len(self.fragments)

    def __iter__(self) -> Iterator[Fragment]:
        return iter(self.fragments)

    @property
    def fragments_ids(self) -> List[int]:
        return list(range(len(self.fragments)))

    class Config:
        arbitrary_types_allowed = True
