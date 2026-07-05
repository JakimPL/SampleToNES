from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from sampletones_core.audio import clip_audio, to_mono
from sampletones_core.library import InstructionLibraryFragment


@dataclass(frozen=True)
class AudioData:
    sample: np.ndarray
    sample_rate: int

    @property
    def samples(self) -> int:
        return len(self.sample)

    @classmethod
    def from_library_fragment(
        cls,
        fragment: InstructionLibraryFragment[Any],
        sample_rate: int,
    ) -> AudioData:
        audio = fragment.data.copy()
        audio = to_mono(audio)
        audio = clip_audio(audio)
        audio = audio.astype(np.float32)
        return cls(
            sample=audio,
            sample_rate=sample_rate,
        )

    @classmethod
    def from_array(cls, sample: np.ndarray, sample_rate: int) -> AudioData:
        return cls(sample=sample.copy(), sample_rate=sample_rate)

    @classmethod
    def empty(cls, sample_rate: int) -> AudioData:
        return cls(
            sample=np.array([], dtype=np.float32),
            sample_rate=sample_rate,
        )

    def is_loaded(self) -> bool:
        return len(self.sample) > 0

    def get_duration_seconds(self) -> float:
        return self.samples / self.sample_rate if self.sample_rate > 0 else 0.0
