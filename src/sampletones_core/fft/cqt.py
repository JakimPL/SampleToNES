from typing import Optional

import librosa
import numpy as np

from sampletones_core.constants.spectrum import (
    BINS_PER_OCTAVE,
    CQT_CUTOFF_FREQUENCY,
)

from .utils import calculate_n_bins, rectangle_window


def calculate_cqt(
    audio: np.ndarray,
    sample_rate: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    n_bins: Optional[int] = None,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
    """
    Compute the Constant-Q Transform of an audio signal.

    The CQT provides logarithmically-spaced frequency bins.
    Uses librosa.cqt with a rectangular window for single-frame analysis.

    If `n_bins` is not provided, it is calculated automatically to cover
    the frequency range from cutoff to Nyquist frequency.

    Args:
        audio: Input audio signal array.
        sample_rate: Sampling rate in Hz.
        cutoff: Minimum frequency in Hz.
        n_bins: Number of frequency bins. If None, calculated automatically.
        bins_per_octave: Number of bins per octave.

    Returns:
        Complex CQT coefficients, shape (n_bins, 1) for single frame.

    Examples:
        >>> audio = np.random.randn(1024)
        >>> cqt = calculate_cqt(audio, 800, cutoff=55.0)
        >>> cqt.ndim
        2
    """
    n_bins = n_bins or calculate_n_bins(sample_rate, cutoff, bins_per_octave)
    hop_length = len(audio) + 1  # a single frame
    return librosa.cqt(
        audio,
        sr=sample_rate,
        fmin=cutoff,
        n_bins=n_bins,
        bins_per_octave=bins_per_octave,
        hop_length=hop_length,
        window=rectangle_window,
    )


def calculate_cqt_frames(
    audio: np.ndarray,
    sample_rate: int,
    hop_length: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    n_bins: Optional[int] = None,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
    """
    Compute the Constant-Q Transform of a whole signal, one column per frame.

    Lets librosa frame and center the transform itself: column ``i`` is centered on
    the frame starting at ``i * hop_length``. Computing the CQT over the whole signal
    is what keeps each frame's energy aligned to its own time position. Extracting a
    per-fragment window and asking librosa for a single column instead reports the
    frame's content offset by roughly half the (very long) constant-Q window.

    Args:
        audio: Input audio signal array.
        sample_rate: Sampling rate in Hz.
        hop_length: Samples between consecutive columns (the frame length).
        cutoff: Minimum frequency in Hz.
        n_bins: Number of frequency bins. If None, calculated automatically.
        bins_per_octave: Number of bins per octave.

    Returns:
        Complex CQT coefficients, shape (n_bins, n_frames).
    """
    n_bins = n_bins or calculate_n_bins(sample_rate, cutoff, bins_per_octave)
    return librosa.cqt(
        audio,
        sr=sample_rate,
        fmin=cutoff,
        n_bins=n_bins,
        bins_per_octave=bins_per_octave,
        hop_length=hop_length,
    )


def calculate_cqt_frequencies(
    n_bins: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
    """
    Calculate center frequencies for CQT bins.

    Computes logarithmically-spaced frequencies for Constant-Q Transform bins.
    Uses librosa.cqt_frequencies which returns the geometric center frequency
    of each bin.

    Args:
        n_bins: Number of frequency bins.
        cutoff: Minimum frequency in Hz.
        bins_per_octave: Number of bins per octave.

    Returns:
        Array of center frequencies in Hz, shape (n_bins,).

    Examples:
        >>> freqs = calculate_cqt_frequencies(12, cutoff=55.0, bins_per_octave=12)
        >>> freqs.shape
        (12,)
        >>> float(freqs[0])
        55.0
        >>> round(float(freqs[-1]), 1)
        103.8
    """
    return librosa.cqt_frequencies(
        n_bins=n_bins,
        fmin=cutoff,
        bins_per_octave=bins_per_octave,
    )


def normalize_cqt_energy(
    energy: np.ndarray,
    frequencies: np.ndarray,
    sample_rate: int,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
    """
    Normalize CQT energy by wavelet lengths.

    Applies a rough normalization based on the quality factor Q and wavelet lengths
    to compensate for varying window sizes across frequency bins. Accepts either a
    single column (shape ``(n_bins,)``) or a stack of per-frame columns
    (shape ``(n_bins, n_frames)``), broadcasting the per-bin wavelet length over any
    trailing frame axis.

    Args:
        energy: Raw CQT energy values, with the bin axis first.
        frequencies: Center frequencies for each bin.
        sample_rate: Sampling rate in Hz.
        bins_per_octave: Number of bins per octave.

    Returns:
        Normalized energy values, same shape as the input.
    """
    q = 1 / (2 ** (1 / bins_per_octave) - 1)
    wavelet_lengths = np.ceil(q * sample_rate / frequencies)
    broadcast_shape = [1] * energy.ndim
    broadcast_shape[0] = wavelet_lengths.shape[0]
    energy_scaled: np.ndarray = 2.0 * energy / wavelet_lengths.reshape(broadcast_shape)
    return energy_scaled


def convert_midpoints_to_edges(midpoints: np.ndarray) -> np.ndarray:
    """
    Convert bin center frequencies to bin edges using geometric mean.

    For logarithmically-spaced frequencies, computes edges as the geometric mean
    of adjacent midpoints. First and last edges are extrapolated.

    Args:
        midpoints: Array of bin center frequencies.

    Returns:
        Array of n + 1 bin edges where n = len(midpoints).

    Examples:
        >>> midpoints = np.array([25.0, 100.0, 400.0])
        >>> edges = convert_midpoints_to_edges(midpoints)
        >>> edges
        array([ 12.5,  50. , 200. , 800. ])
    """
    edges: np.ndarray = np.empty(len(midpoints) + 1)
    edges[1:-1] = np.sqrt(midpoints[:-1] * midpoints[1:])
    edges[0] = midpoints[0] / np.sqrt(midpoints[1] / midpoints[0])
    edges[-1] = midpoints[-1] * np.sqrt(midpoints[-1] / midpoints[-2])
    return edges
