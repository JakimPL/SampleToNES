from __future__ import annotations

from typing import Final

import numpy as np
import pytest

from sampletones_core.fft import erb_bandwidth, k_weighting
from sampletones_core.fft.fft import calculate_weights_from_edges

OCTAVE_EDGES: Final[np.ndarray] = np.geomspace(55.0, 14080.0, 8 * 12 + 1)


class TestErbBandwidth:
    def test_bass_bandwidth_is_nearly_constant(self) -> None:
        """
        Auditory filters keep an almost fixed width below a few hundred hertz, so an
        octave step in the bass changes the bandwidth by a small factor.
        """
        ratio = float(erb_bandwidth(np.array([100.0]))[0] / erb_bandwidth(np.array([50.0]))[0])
        assert ratio < 1.25

    def test_treble_bandwidth_grows_with_frequency(self) -> None:
        """
        Above roughly 500 Hz the bandwidth grows proportionally to frequency, so an
        octave step nearly doubles it.
        """
        ratio = float(erb_bandwidth(np.array([8000.0]))[0] / erb_bandwidth(np.array([4000.0]))[0])
        assert ratio > 1.8


class TestKWeighting:
    def test_response_rises_through_the_bass(self) -> None:
        gains = k_weighting(np.array([30.0, 60.0, 120.0, 250.0]))
        assert bool(np.all(np.diff(gains) > 0.0))

    def test_shelf_boosts_the_treble_over_the_midrange(self) -> None:
        gains = k_weighting(np.array([500.0, 8000.0]))
        assert float(gains[1] / gains[0]) > 2.0

    def test_response_holds_its_plateau_beyond_the_design_nyquist(self) -> None:
        gains = k_weighting(np.array([23000.0, 50000.0, 90000.0]))
        assert float(gains[1]) == pytest.approx(float(gains[0]), rel=0.05)
        assert float(gains[2]) == pytest.approx(float(gains[0]), rel=0.05)

    def test_maximum_gain_is_one(self) -> None:
        gains = k_weighting(np.geomspace(20.0, 20000.0, 256))
        assert float(np.max(gains)) == pytest.approx(1.0)


class TestEdgeWeightDensity:
    def test_octave_bins_carry_fewer_critical_bands_in_the_bass(self) -> None:
        """
        A fixed logarithmic interval covers fewer auditory critical bands at low
        frequencies, so with the perceptual curve switched off, equal-log-width bins
        weigh less in the bass than in the treble.
        """
        weights = calculate_weights_from_edges(OCTAVE_EDGES, perceptual_exponent=0.0)
        centers = np.sqrt(OCTAVE_EDGES[:-1] * OCTAVE_EDGES[1:])
        bass = float(weights[np.argmin(np.abs(centers - 80.0))])
        treble = float(weights[np.argmin(np.abs(centers - 2000.0))])
        assert treble > 1.5 * bass

    def test_equal_linear_widths_weigh_equally_in_the_bass(self) -> None:
        """
        Below a few hundred hertz the auditory bandwidth is nearly constant, so bins
        of equal linear width receive nearly equal density weights.
        """
        edges = np.arange(40.0, 121.0, 10.0)
        weights = calculate_weights_from_edges(edges, perceptual_exponent=0.0)
        assert float(np.max(weights) / np.min(weights)) < 1.35
