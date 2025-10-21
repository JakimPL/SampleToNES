from typing import Iterator, List, Self

import numpy as np
from pydantic import BaseModel, Field

from ffts.fft import calculate_log_arfft, log_arfft_multiply, log_arfft_subtract
from ffts.window import Window


class Fragment(BaseModel):
    audio: np.ndarray = Field(..., description="Windowed audio data of the fragment")
    feature: np.ndarray = Field(..., description="LogARFFT feature of the fragment")
    windowed_audio: np.ndarray = Field(..., description="Original windowed audio data")
    fast_log_arfft: bool = Field(..., description="Whether to use fast LogARFFT operations")

    @classmethod
    def create(cls, windowed_audio: np.ndarray, window: Window, fast_log_arfft: bool = False) -> "Fragment":
        assert windowed_audio.shape[0] == window.size, "Audio length must match window size."
        feature = calculate_log_arfft(windowed_audio, window.size)
        return cls(
            audio=window.get_frame_from_window(windowed_audio),
            feature=feature,
            windowed_audio=windowed_audio,
            fast_log_arfft=fast_log_arfft,
        )

    def __sub__(self, other: Self) -> "Fragment":
        if self.audio.shape != other.audio.shape:
            raise ValueError("Fragments must have the same shape to be subtracted.")

        if self.fast_log_arfft != other.fast_log_arfft:
            raise ValueError("Both fragments must have the same fast_log_arfft setting to be subtracted.")

        windowed_audio = self.windowed_audio - other.windowed_audio
        audio = self.audio - other.audio

        if self.fast_log_arfft:
            feature = log_arfft_subtract(self.feature, other.feature)
        else:
            feature = calculate_log_arfft(windowed_audio)

        return Fragment(audio=audio, feature=feature, windowed_audio=windowed_audio, fast_log_arfft=self.fast_log_arfft)

    def __mul__(self, scalar: float) -> "Fragment":
        audio = self.audio * scalar
        windowed_audio = self.windowed_audio * scalar
        feature = log_arfft_multiply(self.feature, scalar)
        return Fragment(audio=audio, feature=feature, windowed_audio=windowed_audio, fast_log_arfft=self.fast_log_arfft)

    class Config:
        frozen = True
        arbitrary_types_allowed = True


class FragmentedAudio(BaseModel):
    audio: np.ndarray = Field(..., description="Original audio data")
    fragments: list[Fragment] = Field(..., description="List of audio fragments")
    fast_log_arfft: bool = Field(..., description="Whether to use fast LogARFFT operations")

    @classmethod
    def create(cls, audio: np.ndarray, window: Window, fast_log_arfft: bool) -> "FragmentedAudio":
        length = (audio.shape[0] // window.frame_length) * window.frame_length
        audio = audio[:length].copy()
        count = length // window.frame_length
        fragments = [
            Fragment.create(window.get_windowed_frame(audio, fragment_id * window.frame_length), window, fast_log_arfft)
            for fragment_id in range(count)
        ]

        return cls(audio=audio, fragments=fragments, fast_log_arfft=fast_log_arfft)

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
