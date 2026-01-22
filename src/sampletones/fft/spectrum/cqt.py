from typing import Optional

import numpy as np

from sampletones.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones.utils.histogram import Histogram

from ..cqt import calculate_cqt, calculate_frequencies, normalize_cqt_energy


def calculate_nbins(
    sample_rate: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> int:
    """
    Calculate the number of CQT bins needed to cover
    the frequency range up to Nyquist.

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


def calculate_cqt_spectrum(
    audio: np.ndarray,
    sample_rate: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    bins_per_octave: int = BINS_PER_OCTAVE,
    n_bins: Optional[int] = None,
) -> Histogram:
    """
    Calculate the Constant-Q Transform (CQT) spectrum of a wave.

    Computes the CQT with logarithmically-spaced frequency bins,
    with a constant Q factor (ratio of center frequency to bandwidth)
    across all bins.

    Args:
        audio: Input audio as a numpy array.
        fft_size: Size of the FFT.
        sample_rate: Sampling rate in Hz.
        cutoff: Minimum frequency in Hz.
        bins_per_octave: Number of bins per octave.
        n_bins: Number of CQT bins. If None, automatically calculated to reach Nyquist.

    Returns:
        Histogram with log-spaced frequency edges and normalized CQT energy values.

    Raises:
        TypeError: If fft_config or sampling have incorrect types.
    """
    n_bins = n_bins or calculate_nbins(sample_rate, cutoff, bins_per_octave)
    cqt = calculate_cqt(
        audio,
        sample_rate,
        cutoff,
        n_bins,
        bins_per_octave,
    )

    frequencies = calculate_frequencies(
        n_bins,
        cutoff,
        bins_per_octave,
    )

    energy: np.ndarray = np.mean(np.square(np.abs(cqt)), axis=1)
    energy_scaled = normalize_cqt_energy(energy, frequencies, sample_rate, bins_per_octave)
    bands: np.ndarray = convert_midpoints_to_edges(frequencies)
    return Histogram(edges=bands, values=energy_scaled)
