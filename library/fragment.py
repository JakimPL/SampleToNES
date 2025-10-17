from typing import Optional, Self

import numpy as np
from pydantic import BaseModel, Field

from ffts.fft import calculate_log_arfft, log_arfft_multiply, log_arfft_subtract
from ffts.window import Window

FAST_LOG_ARFFT = True


class Fragment(BaseModel):
    audio: np.ndarray = Field(..., description="Windowed audio data of the fragment")
    feature: np.ndarray = Field(..., description="LogARFFT feature of the fragment")
    windowed_audio: np.ndarray = Field(..., description="Original windowed audio data")

    @classmethod
    def create(cls, windowed_audio: np.ndarray, window: Optional[Window] = None) -> Self:
        assert windowed_audio.shape[0] == window.size, "Audio length must match window size."

        size = window.size if window is not None else None
        feature = calculate_log_arfft(windowed_audio, size)
        return cls(
            audio=window.get_frame_from_window(windowed_audio),
            feature=feature,
            windowed_audio=windowed_audio,
        )

    def __sub__(self, other: Self) -> Self:
        if self.audio.shape != other.audio.shape:
            raise ValueError("Fragments must have the same shape to be subtracted.")

        windowed_audio = self.windowed_audio - other.windowed_audio
        audio = self.audio - other.audio
        if FAST_LOG_ARFFT:
            feature = log_arfft_subtract(self.feature, other.feature)
        else:
            feature = calculate_log_arfft(windowed_audio)

        return Fragment(audio=audio, feature=feature, windowed_audio=windowed_audio)

    def __mul__(self, scalar: float) -> Self:
        audio = self.audio * scalar
        windowed_audio = self.windowed_audio * scalar
        feature = log_arfft_multiply(self.feature, scalar)
        return Fragment(audio=audio, feature=feature, windowed_audio=windowed_audio)

    class Config:
        arbitrary_types_allowed = True


class FragmentedAudio(BaseModel):
    audio: np.ndarray = Field(..., description="Original audio data")
    fragments: list[Fragment] = Field(..., description="List of audio fragments")

    @classmethod
    def create(cls, audio: np.ndarray, window: Window) -> Self:
        length = (audio.shape[0] // window.frame_length) * window.frame_length
        audio = audio[:length].copy()
        count = length // window.frame_length
        fragments = [
            Fragment.create(window.get_windowed_frame(audio, fragment_id * window.frame_length), window)
            for fragment_id in range(count)
        ]

        return cls(audio=audio, fragments=fragments)

    def __getitem__(self, index: int) -> Fragment:
        return self.fragments[index]

    def __setitem__(self, index: int, value: Fragment) -> None:
        self.fragments[index] = value

    def __len__(self) -> int:
        return len(self.fragments)

    def __iter__(self):
        return iter(self.fragments)

    class Config:
        arbitrary_types_allowed = True
