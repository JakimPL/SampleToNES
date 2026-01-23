from typing import Optional

import librosa
import numpy as np

from sampletones.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY

from .utils import rectangle_window


def calculate_n_bins(
    sample_rate: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> int:
    """
    Calculate the number of CQT bins needed to cover
    the frequency range up to Nyquist frequency.

    Args:
        cutoff: Minimum frequency in Hz.
        sample_rate: Sampling rate in Hz.
        bins_per_octave: Number of bins per octave.

    Returns:
        Number of bins (floored).
    """
    nyquist = 0.5 * sample_rate
    n_octaves = np.log2(nyquist / cutoff)
    return int(np.floor(n_octaves * bins_per_octave))


def calculate_cqt(
    audio: np.ndarray,
    sample_rate: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    n_bins: Optional[int] = None,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
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


def calculate_frequencies(
    n_bins: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
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
    to compensate for varying window sizes across frequency bins.

    Args:
        energy: Raw CQT energy values.
        frequencies: Center frequencies for each bin.
        sample_rate: Sampling rate in Hz.
        bins_per_octave: Number of bins per octave.

    Returns:
        Normalized energy values.
    """
    q = 1 / (2 ** (1 / bins_per_octave) - 1)
    wavelet_lengths = np.ceil(q * sample_rate / frequencies)
    energy_scaled: np.ndarray = 2.0 * energy / wavelet_lengths
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
    """
    edges: np.ndarray = np.empty(len(midpoints) + 1)
    edges[1:-1] = np.sqrt(midpoints[:-1] * midpoints[1:])
    edges[0] = midpoints[0] / np.sqrt(midpoints[1] / midpoints[0])
    edges[-1] = midpoints[-1] * np.sqrt(midpoints[-1] / midpoints[-2])
    return edges
