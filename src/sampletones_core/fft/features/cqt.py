from __future__ import annotations

from typing import List

import numpy as np

from sampletones_core.constants.spectrum import (
    CQT_REFERENCE_COLUMNS,
    CQT_REFERENCE_CONTEXT_FACTOR,
)
from sampletones_core.structures.histogram import Histogram

from ..fragment.fragment import Fragment
from ..spectrum.cqt import calculate_cqt_spectrum_columns
from ..window.cyclic import CyclicArray
from .base import FeatureExtractor


class CQTFeatureExtractor(FeatureExtractor):
    """
    Whole-signal extraction for the `cqt` method. The constant-Q window spans several
    frames, so the transform runs once over the whole signal, yielding one column per
    frame centered on its hop position. Each frame is aligned to its own time position,
    and `windowed_frames` supplies the frame count.
    """

    def _frame_features(self, audio: np.ndarray, windowed_frames: List[np.ndarray]) -> List[Histogram]:
        spectra = calculate_cqt_spectrum_columns(audio, self.sample_rate, self.window.frame_length)
        return [self.transformer.forward(spectrum) for spectrum in spectra[: len(windowed_frames)]]

    def reference_feature(self, sample: CyclicArray) -> Histogram:
        buffer = sample.get_fragment(0, CQT_REFERENCE_CONTEXT_FACTOR * self.window.size)
        spectra = calculate_cqt_spectrum_columns(buffer, self.sample_rate, self.window.frame_length)
        start = max(0, (len(spectra) - CQT_REFERENCE_COLUMNS) // 2)
        interior = spectra[start : start + CQT_REFERENCE_COLUMNS]
        mean_values = np.mean([histogram.values for histogram in interior], axis=0)
        spectrum = Histogram(edges=interior[0].edges, values=mean_values.astype(np.float32))
        return self.transformer.forward(spectrum)

    def _residual_feature(
        self,
        target: Fragment,
        approximation: Fragment,
        windowed_audio: np.ndarray,
    ) -> Histogram:
        return self.transformer.subtract(target.feature, approximation.feature)
