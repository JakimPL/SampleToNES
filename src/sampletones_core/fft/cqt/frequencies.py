import numpy as np

from sampletones_core.constants.spectrum import (
    BINS_PER_OCTAVE,
    CQT_CUTOFF_FREQUENCY,
)


def calculate_cqt_frequencies(
    n_bins: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
    """
    Calculate center frequencies for CQT bins.

    Bins are spaced geometrically from ``cutoff``, so bin ``k`` sits at
    ``cutoff * 2 ** (k / bins_per_octave)`` — a constant ratio between neighbours that keeps the
    quality factor constant across the spectrum.

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
    exponents: np.ndarray = np.arange(n_bins) / bins_per_octave
    return cutoff * 2.0**exponents


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
