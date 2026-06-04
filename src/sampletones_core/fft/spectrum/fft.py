from typing import Optional

import numpy as np

from sampletones_core.audio import validate_audio_array
from sampletones_core.constants.spectrum import (
    BINS_PER_OCTAVE,
    CQT_CUTOFF_FREQUENCY,
)
from sampletones_core.structures.histogram import Histogram

from ..fft import calculate_fft, calculate_fft_frequencies
from ..utils import calculate_n_bins, to_log_even_bands


def calculate_fft_spectrum(
    audio: np.ndarray,
    sample_rate: int,
    fft_size: Optional[int] = None,
) -> Histogram:
    """
    Calculate the power spectrum of a wave using FFT.

    Computes the real FFT and returns the power spectrum (squared magnitude)
    as a histogram with linearly-spaced frequency bins.

    DC component is excluded.

    Args:
        audio: Input audio as array.
        sample_rate: Sampling rate.
        fft_size: FFT size. If None, uses the length of the audio array.

    Returns:
        Histogram with frequency edges and power spectrum values.
    """
    validate_audio_array(audio)
    fft_size = fft_size or len(audio)
    fft: np.ndarray = calculate_fft(audio, fft_size)
    energy: np.ndarray = np.square(np.abs(fft) / fft_size)
    bands: np.ndarray = calculate_fft_frequencies(fft_size, sample_rate)
    return Histogram(edges=bands.astype(np.float32), values=energy.astype(np.float32))


def calculate_log_spaced_fft_spectrum(
    audio: np.ndarray,
    sample_rate: int,
    fft_size: Optional[int] = None,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    bins_per_octave: int = BINS_PER_OCTAVE,
    n_bins: Optional[int] = None,
) -> Histogram:
    """
    Calculate the power spectrum with logarithmically-spaced frequency bins.

    Computes the linear FFT spectrum and then rebins it to logarithmic scale
    using the configuration parameters.

    Args:
        audio: Input audio as array.
        sample_rate: Sampling rate in Hz.
        fft_size: FFT size. If None, uses the length of the audio array.
        cutoff: Cutoff frequency.
        bins_per_octave: Number of bins per octave. Only used if n_bins is None.
        n_bins: Number of logarithmically spaced components.

    Returns:
        Histogram with log-spaced frequency edges and rebinned power values.

    Raises:
        TypeError: If fft_config or sampling have incorrect types.
    """
    fft_size = fft_size or len(audio)
    n_bins = n_bins or calculate_n_bins(sample_rate, cutoff, bins_per_octave)
    spectrum: Histogram = calculate_fft_spectrum(audio, sample_rate, fft_size)
    log_even_bands: np.ndarray = to_log_even_bands(spectrum.edges, cutoff, n_bins)
    return spectrum.rebin(log_even_bands)
