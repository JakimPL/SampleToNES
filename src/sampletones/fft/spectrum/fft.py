import numpy as np

from sampletones.audio import validate_audio_array
from sampletones.utils.histogram import Histogram

from ..fft import calculate_fft, calculate_frequencies
from ..utils import to_log_even_bands


def calculate_spectrum(
    audio: np.ndarray,
    fft_size: int,
    sample_rate: int,
) -> Histogram:
    """
    Calculate the power spectrum of a wave using FFT.

    Computes the real FFT and returns the power spectrum (squared magnitude)
    as a histogram with linearly-spaced frequency bins.

    DC component is excluded.

    Args:
        audio: Input audio as array.
        fft_size: FFT size.
        sample_rate: Sampling rate.

    Returns:
        Histogram with frequency edges and power spectrum values.
    """
    validate_audio_array(audio)
    fft: np.ndarray = calculate_fft(audio, fft_size)
    energy: np.ndarray = np.square(np.abs(fft) / fft_size)
    bands: np.ndarray = calculate_frequencies(fft_size, sample_rate)
    return Histogram(edges=bands, values=energy)


def calculate_log_spectrum(
    audio: np.ndarray,
    fft_size: int,
    sample_rate: int,
    cutoff: float,
    n_bins: int,
) -> Histogram:
    """
    Calculate the power spectrum with logarithmically-spaced frequency bins.

    Computes the linear FFT spectrum and then rebins it to logarithmic scale
    using the configuration parameters.

    Args:
        audio: Input audio as array.
        fft_size: FFT size.
        sample_rate: Sampling rate.
        cutoff: Cutoff frequency.
        n_bins: Number of logarithmically spaced components.

    Returns:
        Histogram with log-spaced frequency edges and rebinned power values.

    Raises:
        TypeError: If fft_config or sampling have incorrect types.
    """
    spectrum: Histogram = calculate_spectrum(audio, fft_size, sample_rate)
    log_even_bands: np.ndarray = to_log_even_bands(spectrum.edges, cutoff, n_bins)
    return spectrum.rebin(log_even_bands)
