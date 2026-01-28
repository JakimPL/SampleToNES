from __future__ import annotations

from functools import cached_property
from typing import Optional, Tuple, Union

import numpy as np
from pydantic import ConfigDict

from sampletones.configs import Config, InstructionsLibraryConfig
from sampletones.data.model import DataModel
from sampletones.utils import pad

from ..fft import calculate_weights


class Window(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    config: InstructionsLibraryConfig
    on: bool = True
    custom_size: Optional[int] = None

    @property
    def size(self) -> int:
        return self.custom_size if self.custom_size is not None else self.config.window_size

    @cached_property
    def left_offset(self) -> int:
        size = self.size
        return -int(np.ceil((size - self.frame_length) / 2.0))

    @cached_property
    def envelope(self) -> np.ndarray:
        size = self.size
        return self.create_window() if self.on else np.ones(size, dtype=np.float32)

    @cached_property
    def backward_frames(self) -> int:
        return -(self.left_offset // self.config.frame_length)

    @cached_property
    def forward_frames(self) -> int:
        size = self.size
        return -(-(size + self.left_offset) // self.config.frame_length)

    @cached_property
    def weights(self) -> np.ndarray:
        size = self.size
        return calculate_weights(size, self.config.sample_rate)

    @classmethod
    def from_config(
        cls,
        config: Union[Config, InstructionsLibraryConfig],
        on: bool = True,
        custom_size: Optional[int] = None,
    ) -> Window:
        if isinstance(config, InstructionsLibraryConfig):
            return cls(config=config, on=on, custom_size=custom_size)

        if isinstance(config, Config):
            return cls(config=config.library, on=on, custom_size=custom_size)

        raise TypeError("config must be an instance of Config or LibraryConfig")

    def create_window(self) -> np.ndarray:
        frame_length = self.frame_length

        if frame_length < 0 or frame_length > self.size:
            raise ValueError("Frame length must be in [0, total_length]")

        if frame_length == self.size:
            return np.ones(self.size, dtype=np.float32)

        alpha = 1.0 - (frame_length / float(self.size))
        if alpha <= 0.0:
            return np.ones(self.size, dtype=np.float32)

        tapered_total = self.size - frame_length
        left_taper_length = tapered_total // 2
        right_taper_length = tapered_total - left_taper_length

        window = np.zeros(self.size, dtype=np.float32)

        if left_taper_length > 0:
            idx_left = np.arange(left_taper_length)
            window[idx_left] = 0.5 * (1.0 + np.cos(np.pi * (1.0 - (idx_left + 1) / float(left_taper_length))))

        center_start = left_taper_length
        center_end = center_start + frame_length
        window[center_start:center_end] = 1.0

        if right_taper_length > 0:
            idx_right = np.arange(right_taper_length)
            window[center_end + idx_right] = 0.5 * (1.0 + np.cos(np.pi * ((idx_right + 1) / float(right_taper_length))))

        window.setflags(write=False)
        return window

    def get_windowed_frame(
        self,
        audio: np.ndarray,
        offset: int,
        apply_window: bool = True,
    ) -> np.ndarray:
        return self.get_windowed_frame_with_bounds(audio, offset, apply_window=apply_window)[0]

    def get_windowed_frame_with_bounds(
        self,
        audio: np.ndarray,
        offset: int,
        apply_window: bool = True,
    ) -> Tuple[np.ndarray, int, int]:
        left = self.left_offset + offset
        right = left + self.size
        fragment = pad(audio, left, right)

        if apply_window:
            fragment *= self.envelope

        return fragment, max(left, 0), min(right, audio.shape[0])

    def get_frame_from_window(self, audio: np.ndarray, copy: bool = True) -> np.ndarray:
        assert len(audio) == self.size, f"Audio length {len(audio)} must match window size {self.size}"

        left = -self.left_offset
        right = left + self.frame_length
        return audio[left:right].copy() if copy else audio[left:right]

    @property
    def frame_length(self) -> int:
        return self.config.frame_length

    @property
    def sample_rate(self) -> int:
        return self.config.sample_rate
