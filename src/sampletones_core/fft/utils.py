from typing import Optional

import numpy as np

from sampletones_core.constants.spectrum import (
    BINS_PER_OCTAVE,
    CQT_CUTOFF_FREQUENCY,
)
from sampletones_shared.types.array import Array, ArrayClasses, get_array_module


def calculate_n_bins(
    sample_rate: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> int:
    """
    Calculate the number of bins needed to cover
    the frequency range up to Nyquist frequency.

    Args:
        sample_rate: Sampling rate in Hz.
        cutoff: Minimum frequency in Hz.
        bins_per_octave: Number of bins per octave.

    Returns:
        Number of bins (floored).

    Raises:
        ValueError: If cutoff frequency is greater than or equal to Nyquist frequency.
        ValueError: If calculated number of bins is not positive.
    """
    nyquist = 0.5 * sample_rate

    if cutoff >= nyquist:
        raise ValueError(f"Cutoff frequency {cutoff} must be less than Nyquist frequency {nyquist}")

    n_octaves = np.log2(nyquist / cutoff)
    n_bins: int = int(np.floor(n_octaves * bins_per_octave))

    if n_bins <= 0:
        raise ValueError("Calculated number of bins is not positive")

    return n_bins


def rectangle_window(length: int) -> np.ndarray:
    """
    Create a rectangular (uniform) window.

    Args:
        length: Window length.

    Returns:
        Array of ones with the specified length.
    """
    return np.ones(length, dtype=np.float32)


def to_log_even_bands(
    bands: Array,
    cutoff: float,
    n_bins: Optional[int] = None,
) -> Array:
    """
    Generate logarithmically-spaced frequency band edges.

    Creates evenly-spaced bins on a logarithmic scale from cutoff frequency
    to the maximum frequency in the input bands, based on the provided
    array of band edges.

    Returns an array of frequency edges that are logarithmically spaced.
    The number of edges is determined by `n_bins + 1`. If `n_bins` is not provided,
    it defaults to the number of bins in the input array.

    Args:
        bands: Original frequency band edges.
        cutoff: Cutoff frequency.
        n_bins: Number of logarithmically spaced components.

    Returns:
        Array of log-spaced frequency edges.

    Raises:
        TypeError: If bands is not an Array.
        ValueError: If bands has less than two elements.
        ValueError: If bands is not one-dimensional.
        ValueError: If n_bins is provided and is not a positive integer.
        ValueError: If cutoff frequency is greater than or equal to the maximum band frequency.
    """
    if not isinstance(bands, ArrayClasses):
        raise TypeError("bands must be an Array")

    if bands.size < 2:
        raise ValueError("bands array must contain at least two elements")

    if bands.ndim != 1:
        raise ValueError("bands array must be one-dimensional")

    if n_bins is not None and n_bins < 1:
        raise ValueError("n_bins must be a positive integer")

    if cutoff >= bands[-1]:
        raise ValueError("cutoff frequency must be less than the maximum band frequency")

    module = get_array_module(bands)
    size: int = n_bins or len(bands) - 1
    return module.exp(module.linspace(module.log(cutoff), module.log(bands[-1]), size + 1))
