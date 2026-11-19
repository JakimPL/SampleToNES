from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from sampletones_core.audio import clip_audio, to_mono
from sampletones_core.library import InstructionLibraryFragment


@dataclass(frozen=True)
class AudioData:
    """The audio a tab's player sounds, and the tick grid it was rendered on.

    Attributes:
        sample: The audio, one channel.
        sample_rate: How many samples one second spans.
        tick_length: How many samples one tick spans, the distance a step moves the playhead, or ``None``
            for audio laid on no tick grid.
    """

    sample: np.ndarray
    sample_rate: int
    tick_length: Optional[int]

    @property
    def samples(self) -> int:
        return len(self.sample)

    @classmethod
    def from_library_fragment(
        cls,
        fragment: InstructionLibraryFragment[Any],
        sample_rate: int,
        *,
        tick_length: int,
    ) -> AudioData:
        audio = fragment.data.copy()
        audio = to_mono(audio)
        audio = clip_audio(audio)
        audio = audio.astype(np.float32)
        return cls(
            sample=audio,
            sample_rate=sample_rate,
            tick_length=tick_length,
        )

    @classmethod
    def from_array(cls, sample: np.ndarray, sample_rate: int, *, tick_length: Optional[int]) -> AudioData:
        return cls(sample=sample.copy(), sample_rate=sample_rate, tick_length=tick_length)

    @classmethod
    def empty(cls, sample_rate: int) -> AudioData:
        return cls(
            sample=np.array([], dtype=np.float32),
            sample_rate=sample_rate,
            tick_length=None,
        )

    def is_loaded(self) -> bool:
        return len(self.sample) > 0

    def get_duration_seconds(self) -> float:
        return self.samples / self.sample_rate if self.sample_rate > 0 else 0.0
