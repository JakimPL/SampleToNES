import numpy as np
from pydantic import BaseModel, ConfigDict, computed_field

from sampletones.audio import clip_audio, stereo_to_mono
from sampletones.library import LibraryFragment


class AudioData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    sample: np.ndarray
    sample_rate: int
    current_position: int = 0

    @computed_field
    @property
    def samples(self) -> int:
        return len(self.sample)

    @classmethod
    def from_library_fragment(cls, fragment: LibraryFragment, sample_rate: int) -> "AudioData":
        audio = fragment.data.copy()
        audio = stereo_to_mono(audio)
        audio = clip_audio(audio)
        audio = audio.astype(np.float32)
        return cls(
            sample=audio,
            sample_rate=sample_rate,
            current_position=0,
        )

    @classmethod
    def from_array(cls, sample: np.ndarray, sample_rate: int) -> "AudioData":
        return cls(sample=sample.copy(), sample_rate=sample_rate, current_position=0)

    @classmethod
    def empty(cls, sample_rate: int) -> "AudioData":
        return cls(sample=np.array([]), sample_rate=sample_rate, current_position=0)

    def is_loaded(self) -> bool:
        return len(self.sample) > 0

    def get_duration_seconds(self) -> float:
        return self.samples / self.sample_rate if self.sample_rate > 0 else 0.0

    def get_position_seconds(self) -> float:
        return self.current_position / self.sample_rate if self.sample_rate > 0 else 0.0

    def set_position(self, position: int) -> None:
        self.current_position = max(0, min(position, self.samples))

    def set_position_seconds(self, seconds: float) -> None:
        position = int(seconds * self.sample_rate)
        self.set_position(position)

    def reset_position(self) -> None:
        self.current_position = 0
