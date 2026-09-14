from __future__ import annotations

from typing import List

import numpy as np

from sampletones_core.constants.algorithm import LIBRARY_PHASES_PER_SAMPLE
from sampletones_core.structures.histogram import Histogram

from ..fragment.fragment import Fragment
from ..window.cyclic import CyclicArray
from .base import FeatureExtractor


class WindowedFeatureExtractor(FeatureExtractor):
    """
    Per-window extraction for the `fft` and `logfft` methods: each frame's feature is
    computed from its own analysis window, normalized by the envelope energy gain so
    the feature scale is frame-length invariant. (`calculate_spectrum`, invoked
    through the transformer, dispatches between the linear and log-spaced spectra,
    so one class serves both.)
    """

    def _frame_features(self, audio: np.ndarray, windowed_frames: List[np.ndarray]) -> List[Histogram]:
        return [self._windowed_feature(windowed_audio) for windowed_audio in windowed_frames]

    def reference_feature(self, sample: CyclicArray) -> Histogram:
        """The feature of the spectrum the sample averages to over the phases a frame starts on.

        The spectra are averaged as power and the average transformed once, in double precision, so
        the feature is the one of the mean power at every gamma, down to the quietest bins.
        """
        spectra = [
            self._normalized_spectrum(sample.get_windowed_fragment(phase_id / LIBRARY_PHASES_PER_SAMPLE, self.window))
            for phase_id in range(LIBRARY_PHASES_PER_SAMPLE)
        ]
        mean_values = np.mean([spectrum.values for spectrum in spectra], axis=0, dtype=np.float64)
        mean_spectrum = Histogram(edges=spectra[0].edges.astype(np.float64), values=mean_values)
        return self.transformer.forward(mean_spectrum).astype(np.float32)

    def _residual_feature(
        self,
        target: Fragment,
        approximation: Fragment,
        windowed_audio: np.ndarray,
    ) -> Histogram:
        if self.config.generation.calculation.fast_difference:
            return self.transformer.subtract(target.feature, approximation.feature)

        return self._windowed_feature(windowed_audio)

    def _windowed_feature(self, windowed_audio: np.ndarray) -> Histogram:
        """
        Feature of one analysis window, normalized by the envelope energy gain.

        The raw power spectrum of a windowed frame scales with `mean(envelope**2)`;
        dividing the spectrum by that gain before the feature transform makes a given
        signal produce the same feature at every NES frequency, keeping the spectral
        scale, the spectrum floor, and the divergence semantics frame-rate stable.
        """
        return self.transformer.forward(self._normalized_spectrum(windowed_audio))

    def _normalized_spectrum(self, windowed_audio: np.ndarray) -> Histogram:
        """The power spectrum of one analysis window, divided by the envelope energy gain."""
        gain = self.window.energy_gain
        spectrum = self.transformer.calculate_spectrum(windowed_audio, self.sample_rate)
        return spectrum.apply_with(lambda values: values / gain)
