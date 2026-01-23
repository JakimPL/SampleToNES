from typing import Optional

import numpy as np

from sampletones.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY


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


def rectangle_window(length: int) -> np.ndarray:
    """
    Create a rectangular (uniform) window.

    Args:
        length: Window length.

    Returns:
        Array of ones with the specified length.
    """
    return np.ones(length, dtype=float)


def to_log_even_bands(
    bands: np.ndarray,
    cutoff: float,
    n_bins: Optional[int] = None,
) -> np.ndarray:
    """
    Generate logarithmically-spaced frequency band edges.

    Creates evenly-spaced bins on a logarithmic scale from cutoff frequency
    to the maximum frequency in the input bands.

    Args:
        bands: Original frequency band edges.
        cutoff: Cutoff frequency.
        n_bins: Number of logarithmically spaced components.
        bins_per_octave: Number of bins per octave.

    Returns:
        Array of log-spaced frequency edges.
    """
    size: int = n_bins or len(bands) - 1
    return np.exp(np.linspace(np.log(cutoff), np.log(bands[-1]), size + 1))
