from __future__ import annotations

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones_core.fft import (
    FFTTransformer,
    Window,
    calculate_fft_frequencies,
    calculate_weights,
    calculate_weights_from_edges,
)
from sampletones_core.fft.features import get_feature_extractor


def _config(method: SpectrumMethod) -> Config:
    base = Config()
    return base.model_copy(
        update={"library": base.library.model_copy(update={"nes_frequency": 60, "spectrum_method": method})}
    )


def _signal(window: Window) -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.standard_normal(window.size).astype(np.float32)


class TestWindowSizeRule:
    def test_cqt_window_is_longer_than_fft(self) -> None:
        assert _config(SpectrumMethod.CQT).library.window_size > _config(SpectrumMethod.FFT).library.window_size

    def test_cqt_window_holds_the_lowest_filter(self) -> None:
        library = _config(SpectrumMethod.CQT).library
        quality = 1.0 / (2.0 ** (1.0 / BINS_PER_OCTAVE) - 1.0)
        expected = int(np.ceil(quality * library.sample_rate / CQT_CUTOFF_FREQUENCY))
        assert library.window_size == max(library.frame_length, expected)


class TestFragmentAxis:
    def test_fft_feature_edges_reach_nyquist(self) -> None:
        config = _config(SpectrumMethod.FFT)
        window = Window.from_config(config)
        fragment = get_feature_extractor(config, window).extract(_signal(window))[0]
        nyquist = config.library.sample_rate / 2.0
        assert float(fragment.feature.edges[-1]) == pytest.approx(nyquist, rel=1e-3)

    def test_cqt_feature_shares_the_library_frequency_axis(self) -> None:
        config = _config(SpectrumMethod.CQT)
        window = Window.from_config(config)
        signal = _signal(window)

        fragment = get_feature_extractor(config, window).extract(signal)[0]
        transformer = FFTTransformer.from_gamma(
            config.library.transformation_gamma,
            config.library.sample_rate,
            SpectrumMethod.CQT,
        )
        reference = transformer.calculate_feature(signal, config.library.sample_rate)

        assert np.array_equal(np.asarray(fragment.feature.edges), np.asarray(reference.edges))
        assert len(fragment.feature.values) > 1


class TestEdgeWeights:
    def test_reproduces_linear_fft_weights(self) -> None:
        sample_rate, length = 44100, 1024
        edges = calculate_fft_frequencies(length, sample_rate)
        from_edges = calculate_weights_from_edges(edges, perceptual_exponent=1.0)
        linear = calculate_weights(length, sample_rate, 1.0)
        assert np.allclose(from_edges, linear, atol=1e-6)

    def test_cqt_edges_give_positive_normalized_weights(self) -> None:
        config = _config(SpectrumMethod.CQT)
        transformer = FFTTransformer.from_gamma(0, config.library.sample_rate, SpectrumMethod.CQT)
        zeros = np.zeros(config.library.window_size, dtype=np.float32)
        edges = np.asarray(transformer.calculate_feature(zeros, config.library.sample_rate).edges)

        weights = calculate_weights_from_edges(edges)
        assert weights.shape[0] == len(edges) - 1
        assert bool(np.all(weights > 0.0))
        assert float(weights.sum()) == pytest.approx(1.0)
