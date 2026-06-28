from __future__ import annotations

from typing import List

import numpy as np

from sampletones_core.constants.general import LIBRARY_PHASES_PER_SAMPLE
from sampletones_core.structures.histogram import Histogram

from ..fragment.fragment import Fragment
from ..window.cyclic import CyclicArray
from .base import FeatureExtractor


class WindowedFeatureExtractor(FeatureExtractor):
    """
    Per-window extraction for the `fft` and `logfft` methods: each frame's feature is
    computed from its own analysis window. (`calculate_spectrum`, invoked through the
    transformer, dispatches between the linear and log-spaced spectra, so one class
    serves both.)
    """

    def _frame_features(self, audio: np.ndarray, windowed_frames: List[np.ndarray]) -> List[Histogram]:
        return [
            self.transformer.calculate_feature(windowed_audio, self.sample_rate) for windowed_audio in windowed_frames
        ]

    def reference_feature(self, sample: CyclicArray) -> Histogram:
        features: List[Histogram] = []
        for phase_id in range(LIBRARY_PHASES_PER_SAMPLE):
            phase = phase_id / LIBRARY_PHASES_PER_SAMPLE
            windowed_audio = sample.get_windowed_fragment(phase, self.window)
            features.append(self.transformer.calculate_feature(windowed_audio, self.sample_rate))

        return self.transformer.mean(features)

    def _residual_feature(
        self,
        target: Fragment,
        approximation: Fragment,
        windowed_audio: np.ndarray,
    ) -> Histogram:
        if self.config.generation.calculation.fast_difference:
            return self.transformer.subtract(target.feature, approximation.feature)

        return self.transformer.calculate_feature(windowed_audio, self.sample_rate)
