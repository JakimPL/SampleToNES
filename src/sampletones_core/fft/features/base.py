from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.structures.histogram import Histogram

from ..fragment.fragment import Fragment
from ..transformer import FFTTransformer
from ..window.cyclic import CyclicArray
from ..window.window import Window


class FeatureExtractor(ABC):
    """
    Owns the conversion of audio into per-frame spectral features for one spectrum
    method.

    A single extractor produces the matching target's per-frame features
    (`extract`) and a stationary candidate's reference feature (`reference_feature`).
    Routing the target and the library through the same extractor is what keeps the
    two directly comparable, and confines all spectrum-method branching to the
    extractor chosen for the configuration.
    """

    def __init__(self, config: Config, window: Window) -> None:
        self.config = config
        self.window = window
        self.transformer = FFTTransformer.from_gamma(
            config.library.transformation_gamma,
            config.library.sample_rate,
            config.library.spectrum_method,
        )

    @property
    def sample_rate(self) -> int:
        return self.config.library.sample_rate

    def extract(self, audio: np.ndarray) -> List[Fragment]:
        """
        Build one `Fragment` per frame of `audio` (its central slice, its analysis
        window, and its spectral feature).
        """
        frame_length = self.window.frame_length
        count = audio.shape[0] // frame_length
        if count == 0:
            return []

        windowed_frames = [self.window.get_windowed_frame(audio, frame_id * frame_length) for frame_id in range(count)]
        features = self._frame_features(audio, windowed_frames)
        return [
            Fragment(
                audio=self.window.get_frame_from_window(windowed_audio),
                feature=feature,
                windowed_audio=windowed_audio,
                config=self.config,
            )
            for windowed_audio, feature in zip(windowed_frames, features)
        ]

    @abstractmethod
    def _frame_features(
        self,
        audio: np.ndarray,
        windowed_frames: List[np.ndarray],
    ) -> List[Histogram]:
        """Per-frame features; `windowed_frames` are the frame-centered analysis windows."""

    @abstractmethod
    def reference_feature(self, sample: CyclicArray) -> Histogram:
        """Steady-state feature of a stationary, periodic candidate sample."""
