import numpy as np
import pytest

from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones_core.fft.cqt.frequencies import calculate_cqt_frequencies
from sampletones_core.fft.cqt.transform import calculate_cqt, calculate_cqt_frames
from sampletones_core.fft.spectrum.cqt import calculate_cqt_spectrum_columns
from sampletones_core.fft.utils import calculate_n_bins

SAMPLE_RATE = 22050
HOP_LENGTH = 512


def _bin_count() -> int:
    return calculate_n_bins(SAMPLE_RATE, CQT_CUTOFF_FREQUENCY, BINS_PER_OCTAVE)


def _bin_frequencies() -> np.ndarray:
    return calculate_cqt_frequencies(_bin_count(), CQT_CUTOFF_FREQUENCY, BINS_PER_OCTAVE)


def _tone(frequency: float, length: int) -> np.ndarray:
    samples = np.arange(length)
    return np.cos(2.0 * np.pi * frequency * samples / SAMPLE_RATE).astype(np.float32)


class TestForwardTransform:
    def test_peak_lands_on_the_tone_bin(self) -> None:
        frequencies = _bin_frequencies()
        target = _bin_count() // 2
        signal = _tone(float(frequencies[target]), SAMPLE_RATE)
        cqt = calculate_cqt_frames(signal, SAMPLE_RATE, HOP_LENGTH)
        energy = np.mean(np.abs(cqt) ** 2, axis=1)
        assert int(np.argmax(energy)) == target

    def test_shape_and_complex_dtype(self) -> None:
        signal = _tone(440.0, SAMPLE_RATE)
        cqt = calculate_cqt_frames(signal, SAMPLE_RATE, HOP_LENGTH)
        assert cqt.shape == (_bin_count(), 1 + len(signal) // HOP_LENGTH)
        assert np.iscomplexobj(cqt)

    def test_single_frame_returns_one_column(self) -> None:
        signal = _tone(440.0, 4096)
        cqt = calculate_cqt(signal, SAMPLE_RATE)
        assert cqt.shape == (_bin_count(), 1)


class TestToneNormalization:
    def test_normalized_peak_is_bin_comparable(self) -> None:
        frequencies = _bin_frequencies()
        low_bin, high_bin = _bin_count() // 3, 2 * _bin_count() // 3

        peaks = []
        for bin_index in (low_bin, high_bin):
            signal = _tone(float(frequencies[bin_index]), 2 * SAMPLE_RATE)
            spectra = calculate_cqt_spectrum_columns(signal, SAMPLE_RATE, HOP_LENGTH)
            values = np.mean([spectrum.values for spectrum in spectra], axis=0)
            assert int(np.argmax(values)) == bin_index
            peaks.append(float(values[bin_index]))

        assert peaks[0] == pytest.approx(peaks[1], rel=0.3)


class TestLibrosaParity:
    def test_energy_shape_correlates_with_librosa(self) -> None:
        import librosa

        n_bins = _bin_count()
        rng = np.random.default_rng(0)
        signal = rng.standard_normal(SAMPLE_RATE).astype(np.float32)

        ours = np.mean(np.abs(calculate_cqt_frames(signal, SAMPLE_RATE, HOP_LENGTH)) ** 2, axis=1)
        reference = librosa.cqt(
            signal,
            sr=SAMPLE_RATE,
            fmin=CQT_CUTOFF_FREQUENCY,
            n_bins=n_bins,
            bins_per_octave=BINS_PER_OCTAVE,
            hop_length=HOP_LENGTH,
        )
        reference_energy = np.mean(np.abs(reference) ** 2, axis=1)

        upper = slice(n_bins // 2, n_bins)
        correlation = float(np.corrcoef(ours[upper], reference_energy[upper])[0, 1])
        assert correlation > 0.95
