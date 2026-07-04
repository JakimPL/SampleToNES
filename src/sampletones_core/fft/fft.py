from typing import Final, Optional, Tuple, cast

import numpy as np
from scipy.fft import rfft, rfftfreq

from sampletones_core.constants.spectrum import ERB_FREQUENCY_FACTOR, ERB_MINIMUM_BANDWIDTH

K_WEIGHTING_SAMPLE_RATE: Final[float] = 48000.0
K_SHELF_NUMERATOR: Final[Tuple[float, float, float]] = (1.53512485958697, -2.69169618940638, 1.19839281085285)
K_SHELF_DENOMINATOR: Final[Tuple[float, float, float]] = (1.0, -1.69065929318241, 0.73248077421585)
K_HIGHPASS_NUMERATOR: Final[Tuple[float, float, float]] = (1.0, -2.0, 1.0)
K_HIGHPASS_DENOMINATOR: Final[Tuple[float, float, float]] = (1.0, -1.99004745483398, 0.99007225036621)


def calculate_fft(audio: np.ndarray, fft_size: Optional[int] = None) -> np.ndarray:
    """
    Compute the real-valued Fast Fourier Transform of an audio signal.

    Calculates the FFT and removes the DC component (first element).
    Uses scipy.fft.rfft which is optimized for real-valued input signals.

    Args:
        audio: Input audio signal array.
        fft_size: Size of the FFT. If None, uses the length of the audio array.

    Returns:
        Complex FFT coefficients with DC component removed, shape (fft_size//2,).

    Examples:
        >>> audio = np.random.randn(1024)
        >>> fft_result = calculate_fft(audio)
        >>> fft_result.shape
        (512,)
    """
    fft_size = audio.shape[0] if fft_size is None else fft_size
    array = cast(np.ndarray, rfft(audio, fft_size))
    return array[1:]


def calculate_fft_frequencies(fragment_length: int, sample_rate: int) -> np.ndarray:
    """
    Calculate frequency bins for a real-valued FFT.

    Computes the frequencies corresponding to each FFT bin for a real signal.
    Uses scipy.fft.rfftfreq which returns positive frequencies only.

    Returns frequency edges from 0 Hz up to Nyquist frequency.

    Args:
        fragment_length: Length of the audio fragment (FFT size).
        sample_rate: Sampling rate in Hz.

    Returns:
        Array of frequency values in Hz, shape (fragment_length//2 + 1,).

    Examples:
        >>> freqs = calculate_fft_frequencies(1024, 44100)
        >>> freqs.shape
        (513,)
        >>> float(freqs[0])
        0.0
        >>> float(freqs[-1])
        22050.0
    """
    frequencies: np.ndarray = rfftfreq(fragment_length, 1.0 / sample_rate)
    return frequencies


def erb_bandwidth(frequencies: np.ndarray) -> np.ndarray:
    """
    Equivalent rectangular bandwidth of the auditory filter centered at each frequency.

    Follows the Glasberg-Moore formula `24.7 * (1 + 4.37 * f / 1000)`: the bandwidth
    stays near 25 Hz in the bass and grows proportionally to frequency above roughly
    500 Hz, matching how the ear allocates spectral resolution.

    Args:
        frequencies: Array of frequency values in Hz.

    Returns:
        Auditory filter bandwidth in Hz, shape matching the input.

    Examples:
        >>> bandwidths = erb_bandwidth(np.array([100.0, 1000.0]))
        >>> bandwidths.shape
        (2,)
    """
    return ERB_MINIMUM_BANDWIDTH * (1.0 + ERB_FREQUENCY_FACTOR * np.asarray(frequencies, dtype=np.float64))


def _biquad_power_response(
    omega: np.ndarray,
    numerator: Tuple[float, float, float],
    denominator: Tuple[float, float, float],
) -> np.ndarray:
    delay = np.exp(-1j * omega)
    response_numerator = numerator[0] + numerator[1] * delay + numerator[2] * delay**2
    response_denominator = denominator[0] + denominator[1] * delay + denominator[2] * delay**2
    response: np.ndarray = (np.abs(response_numerator) / np.abs(response_denominator)) ** 2
    return response


def k_weighting(frequencies: np.ndarray) -> np.ndarray:
    """
    K-weighting power response (ITU-R BS.1770) at the given frequencies.

    Evaluates the standard's two pre-filter stages - the high-frequency shelf and
    the RLB high-pass - at their 48 kHz design rate and returns the combined power
    gain, normalized to a maximum of one. The curve models loudness at typical
    music listening levels: a gentle roll-off below roughly 100 Hz and a +4 dB
    shelf above 2 kHz. Frequencies at or beyond the design Nyquist hold the
    response at its plateau.

    Args:
        frequencies: Array of frequency values in Hz.

    Returns:
        Normalized K-weighting power gains in [0, 1], shape matching the input.

    Examples:
        >>> gains = k_weighting(np.array([100.0, 1000.0, 10000.0]))
        >>> gains.shape
        (3,)
    """
    omega = np.minimum(np.pi, 2.0 * np.pi * np.asarray(frequencies, dtype=np.float64) / K_WEIGHTING_SAMPLE_RATE)
    power = _biquad_power_response(omega, K_SHELF_NUMERATOR, K_SHELF_DENOMINATOR) * _biquad_power_response(
        omega, K_HIGHPASS_NUMERATOR, K_HIGHPASS_DENOMINATOR
    )
    normalized_power: np.ndarray = power / np.max(power)
    return normalized_power


def calculate_weights_from_edges(edges: np.ndarray, perceptual_exponent: float = 1.0) -> np.ndarray:
    """
    Calculate perceptual frequency weights for arbitrary histogram bin edges.

    Works for any frequency axis (linear FFT or logarithmic CQT). Each bin is
    weighted by its span in auditory critical bands, `width / erb_bandwidth(f)`
    (the number of ERBs the bin covers), times the K-weighting power response
    raised to `perceptual_exponent`. The ERB measure follows a logarithmic axis
    above roughly 500 Hz and a linear one below, matching the ear's resolution;
    the K curve weights each band by its contribution to loudness at typical
    music listening levels.

    The result is normalized to sum to 1.0.

    Args:
        edges: Strictly increasing bin edges, shape (n_bins + 1,).
        perceptual_exponent: Power applied to the K-weighting curve.

    Returns:
        Normalized weights, shape (n_bins,). Sum of weights equals 1.0.

    Examples:
        >>> edges = calculate_fft_frequencies(1024, 44100)
        >>> weights = calculate_weights_from_edges(edges)
        >>> weights.shape
        (512,)
        >>> bool(np.isclose(weights.sum(), 1.0))
        True
    """
    frequencies = edges[1:]
    widths = np.diff(edges)
    density_weights = widths / erb_bandwidth(frequencies)
    perceptual_weights = k_weighting(frequencies) ** perceptual_exponent

    weights: np.ndarray = density_weights * perceptual_weights
    normalized_weights: np.ndarray = weights / np.sum(weights)
    return normalized_weights
