from dataclasses import dataclass
from typing import Final, Tuple

import numpy as np
import pytest

from sampletones_core.constants.algorithm import PERCEPTUAL_EXPONENT
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones_core.fft.cqt.frequencies import calculate_cqt_frequencies
from sampletones_core.fft.utils import calculate_n_bins
from tests.suite.case import BaseTestCase
from tests.unit.sampletones_core.fft.spectral_probe import (
    PROBE_TONE_AMPLITUDE,
    SpectrumProbe,
    band_energy,
    bin_value_at,
    octave_weight_shares,
)

SAMPLE_RATE: Final[int] = 22050
NES_FREQUENCY: Final[int] = 30
BAND_RADIUS: Final[int] = 2
NOISE_DRAWS: Final[int] = 8

OCTAVE_BANDS: Final[Tuple[Tuple[float, float], ...]] = (
    (55.0, 110.0),
    (110.0, 220.0),
    (220.0, 440.0),
    (440.0, 880.0),
    (880.0, 1760.0),
    (1760.0, 3520.0),
    (3520.0, 7040.0),
)


def probe(
    method: SpectrumMethod,
    nes_frequency: int = NES_FREQUENCY,
) -> SpectrumProbe:
    return SpectrumProbe(
        sample_rate=SAMPLE_RATE,
        nes_frequency=nes_frequency,
        method=method,
    )


class TestToneResponseFlatness:
    @dataclass(frozen=True, kw_only=True)
    class FlatnessCase(BaseTestCase):
        label: str
        method: SpectrumMethod
        frequencies: Tuple[float, ...]
        tolerance_ratio: float

    test_cases = (
        FlatnessCase(
            label="fft",
            method=SpectrumMethod.FFT,
            frequencies=(110.0, 440.0, 1760.0, 7040.0),
            tolerance_ratio=1.35,
        ),
        FlatnessCase(
            label="logfft",
            method=SpectrumMethod.LOG_SPACED_FFT,
            frequencies=(110.0, 440.0, 1760.0, 7040.0),
            tolerance_ratio=1.35,
        ),
        FlatnessCase(
            label="cqt",
            method=SpectrumMethod.CQT,
            frequencies=(110.0, 440.0, 1760.0, 7040.0),
            tolerance_ratio=1.2,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_tone_band_energy_is_flat_across_frequency(
        self,
        case: FlatnessCase,
    ) -> None:
        spectrum_probe = probe(case.method)
        responses = [
            band_energy(
                spectrum_probe.tone_spectrum(frequency),
                frequency,
                radius=BAND_RADIUS,
            )
            for frequency in case.frequencies
        ]
        assert max(responses) / min(responses) < case.tolerance_ratio

    def test_low_tones_stay_compact_on_the_resolution_floored_log_axis(self) -> None:
        """
        The log axis floors its bin widths at the FFT resolution, so a low tone's
        energy aggregates into full-width bins and its band energy matches the band
        energy the same tone produces higher up the axis.
        """
        spectrum_probe = probe(SpectrumMethod.LOG_SPACED_FFT)
        low = band_energy(
            spectrum_probe.tone_spectrum(110.0),
            110.0,
            radius=BAND_RADIUS,
        )
        reference = band_energy(
            spectrum_probe.tone_spectrum(440.0),
            440.0,
            radius=BAND_RADIUS,
        )
        assert 0.75 < low / reference < 1.35


class TestNoiseScaling:
    @dataclass(frozen=True, kw_only=True)
    class NoiseScalingCase(BaseTestCase):
        label: str
        method: SpectrumMethod
        lower_frequency: float
        upper_frequency: float
        expected_ratio_range: Tuple[float, float]

    test_cases = (
        NoiseScalingCase(
            label="fft-flat-per-bin",
            method=SpectrumMethod.FFT,
            lower_frequency=440.0,
            upper_frequency=7040.0,
            expected_ratio_range=(0.25, 4.0),
        ),
        NoiseScalingCase(
            label="logfft-proportional-to-bandwidth",
            method=SpectrumMethod.LOG_SPACED_FFT,
            lower_frequency=440.0,
            upper_frequency=7040.0,
            expected_ratio_range=(8.0, 32.0),
        ),
        NoiseScalingCase(
            label="cqt-proportional-to-bandwidth",
            method=SpectrumMethod.CQT,
            lower_frequency=440.0,
            upper_frequency=7040.0,
            expected_ratio_range=(8.0, 32.0),
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_noise_bin_values_scale_with_the_bin_bandwidth(
        self,
        case: NoiseScalingCase,
    ) -> None:
        """
        White noise reads flat per bin on the linear axis and proportionally to the
        bin bandwidth on the logarithmic axes, where each bin integrates the noise
        power over a span growing with frequency.
        """
        spectrum = probe(case.method).mean_noise_spectrum(draws=NOISE_DRAWS)
        lower = band_energy(spectrum, case.lower_frequency, radius=BAND_RADIUS)
        upper = band_energy(spectrum, case.upper_frequency, radius=BAND_RADIUS)
        ratio = upper / lower
        assert case.expected_ratio_range[0] < ratio < case.expected_ratio_range[1]


class TestOctaveWeightAllocation:
    def test_weight_shares_match_across_spectrum_methods(self) -> None:
        """
        The criterion weighting allocates the same share of attention to each octave
        for every spectrum method: the density term converts each method's axis to a
        common auditory measure before the perceptual curve applies. The tolerance
        leaves room for bin-granularity effects where the perceptual curve changes
        fastest (the K-weighting shelf knee around 2 kHz).
        """
        shares_per_method = []
        for method in (
            SpectrumMethod.FFT,
            SpectrumMethod.LOG_SPACED_FFT,
            SpectrumMethod.CQT,
        ):
            edges = np.asarray(probe(method).tone_spectrum(440.0).edges)
            shares = np.asarray(
                octave_weight_shares(
                    edges,
                    perceptual_exponent=PERCEPTUAL_EXPONENT,
                    bands=OCTAVE_BANDS,
                )
            )
            shares_per_method.append(shares / shares.sum())

        for shares in shares_per_method[1:]:
            assert np.max(np.abs(shares - shares_per_method[0])) < 0.03

    def test_weight_shares_are_stable_across_window_sizes(self) -> None:
        shares_per_window = []
        for nes_frequency in (15, 30):
            edges = np.asarray(probe(SpectrumMethod.FFT, nes_frequency).tone_spectrum(440.0).edges)
            shares = np.asarray(
                octave_weight_shares(
                    edges,
                    perceptual_exponent=PERCEPTUAL_EXPONENT,
                    bands=OCTAVE_BANDS,
                )
            )
            shares_per_window.append(shares / shares.sum())

        assert np.max(np.abs(shares_per_window[1] - shares_per_window[0])) < 0.02


class TestWindowScaling:
    def test_cqt_tone_response_is_frame_length_invariant(self) -> None:
        """
        Constant-Q wavelet lengths depend on frequency alone, so the frame length
        only positions the analysis columns and the tone response stays constant
        across NES frequencies.
        """
        responses = [
            band_energy(
                probe(SpectrumMethod.CQT, nes_frequency).tone_spectrum(440.0),
                440.0,
                radius=BAND_RADIUS,
            )
            for nes_frequency in (30, 60, 300)
        ]
        assert max(responses) / min(responses) < 1.2

    def test_fft_tone_response_is_frame_length_invariant(self) -> None:
        """
        The envelope energy-gain normalization makes the windowed methods report the
        same tone energy at every NES frequency, matching the constant-Q behavior.
        """
        responses = [
            band_energy(
                probe(SpectrumMethod.FFT, nes_frequency).tone_spectrum(440.0),
                440.0,
                radius=BAND_RADIUS,
            )
            for nes_frequency in (30, 60, 300)
        ]
        assert max(responses) / min(responses) < 1.2

    def test_uniform_envelope_has_unit_energy_gain(self) -> None:
        """
        At an NES frequency whose frame fills the whole window, the envelope is
        uniform and the normalization leaves the spectrum unchanged.
        """
        assert probe(SpectrumMethod.FFT, 15).window.energy_gain == pytest.approx(1.0)


class TestScaleConventions:
    def test_fft_bin_centered_tone_reports_half_of_the_squared_amplitude(self) -> None:
        """
        The one-sided power spectrum reports a bin-centered tone of amplitude ``A``
        as a single bin of value ``A ** 2 / 2`` — the tone's mean-square power —
        matching the constant-Q convention.
        """
        spectrum_probe = probe(SpectrumMethod.FFT, 15)
        bin_width = SAMPLE_RATE / spectrum_probe.window.size
        frequency = 30 * bin_width
        spectrum = spectrum_probe.tone_spectrum(frequency)
        expected = PROBE_TONE_AMPLITUDE**2 / 2.0
        assert bin_value_at(spectrum, frequency) == pytest.approx(
            expected,
            rel=0.05,
        )

    def test_cqt_bin_centered_tone_reports_half_of_the_squared_amplitude(self) -> None:
        """
        The constant-Q normalization reports a bin-centered tone of amplitude ``A``
        as ``A ** 2 / 2`` — the tone's mean-square power — matching the linear-FFT
        convention.
        """
        n_bins = calculate_n_bins(
            SAMPLE_RATE,
            CQT_CUTOFF_FREQUENCY,
            BINS_PER_OCTAVE,
        )
        frequencies = calculate_cqt_frequencies(
            n_bins,
            CQT_CUTOFF_FREQUENCY,
            BINS_PER_OCTAVE,
        )
        frequency = float(frequencies[int(np.argmin(np.abs(frequencies - 440.0)))])
        spectrum = probe(SpectrumMethod.CQT).tone_spectrum(frequency)
        expected = PROBE_TONE_AMPLITUDE**2 / 2.0
        assert bin_value_at(spectrum, frequency) == pytest.approx(
            expected,
            rel=0.15,
        )
