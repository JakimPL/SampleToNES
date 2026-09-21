from typing import Final

import numpy as np
import pytest
from scipy.signal import stft

from sampletones_tools.calibration.config.referee import RefereeConfig
from sampletones_tools.calibration.referee.bands import BandAnalyzer

from .conftest import SAMPLE_RATE, ProbeSignals

TONE_BAND_SHARE: Final[float] = 0.9


@pytest.fixture(scope="module", name="analyzer")
def analyzer_fixture(referee_config: RefereeConfig) -> BandAnalyzer:
    return BandAnalyzer(SAMPLE_RATE, config=referee_config)


class TestBandAnalyzer:
    def test_every_configured_window_size_is_analyzed(
        self, analyzer: BandAnalyzer, referee_config: RefereeConfig
    ) -> None:
        assert analyzer.window_sizes == referee_config.window_sizes

    def test_band_energies_hold_every_bin_once(
        self,
        analyzer: BandAnalyzer,
        referee_config: RefereeConfig,
        probes: ProbeSignals,
    ) -> None:
        """The bands partition the spectrum, so per frame they sum to the STFT's whole energy."""
        window_size = referee_config.window_sizes[0]
        _, _, spectrum = stft(
            probes.noise,
            fs=SAMPLE_RATE,
            nperseg=window_size,
            noverlap=window_size - window_size // referee_config.hop_divisor,
        )

        energies = analyzer.band_energies(probes.noise, window_size)

        assert energies.shape == (referee_config.band_count, spectrum.shape[1])
        assert np.allclose(energies.sum(axis=0), (np.abs(spectrum) ** 2).sum(axis=0))

    def test_a_tone_fills_the_band_of_its_frequency(
        self,
        analyzer: BandAnalyzer,
        referee_config: RefereeConfig,
        probes: ProbeSignals,
    ) -> None:
        energies = analyzer.band_energies(probes.sine, referee_config.window_sizes[-1]).sum(axis=1)
        assert np.max(energies) > TONE_BAND_SHARE * np.sum(energies)

    def test_the_audibility_floor_sits_the_range_under_the_loudest_band(
        self,
        analyzer: BandAnalyzer,
        referee_config: RefereeConfig,
    ) -> None:
        energies = np.array([[1.0, 4.0], [0.5, 2.0]])
        floor = analyzer.audibility_floor(energies, range_decibels=30.0)
        assert floor == pytest.approx(4.0e-3)

    def test_a_silent_reference_keeps_a_finite_floor(
        self,
        analyzer: BandAnalyzer,
        referee_config: RefereeConfig,
    ) -> None:
        floor = analyzer.audibility_floor(np.zeros((2, 3)), range_decibels=10.0)
        assert floor == pytest.approx(referee_config.energy_floor * 0.1)
