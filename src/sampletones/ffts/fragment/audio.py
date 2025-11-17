from typing import List

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones.configs import Config

from ..window.window import Window
from .fragment import Fragment


class FragmentedAudio(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    audio: np.ndarray = Field(..., description="Original audio data")
    fragments: List[Fragment] = Field(..., description="List of audio fragments")
    config: Config = Field(..., description="Configuration")

    @classmethod
    def create(cls, audio: np.ndarray, config: Config, window: Window) -> "FragmentedAudio":
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
