from functools import lru_cache
from typing import Tuple

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


@lru_cache(maxsize=128)
def _resolution_floored_edges(
    maximum: float,
    cutoff: float,
    bins_per_octave: int,
    resolution: float,
) -> Tuple[float, ...]:
    ratio = 2.0 ** (1.0 / bins_per_octave)
    edges = [cutoff]
    while edges[-1] < maximum:
        edges.append(min(maximum, max(edges[-1] * ratio, edges[-1] + resolution)))

    return tuple(edges)


def to_resolution_floored_log_bands(
    bands: Array,
    cutoff: float,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> Array:
    """
    Generate logarithmically-spaced band edges whose widths respect the source resolution.

    Edges advance from the cutoff frequency by a factor of `2 ** (1 / bins_per_octave)`
    or by the source band spacing, whichever is larger, up to the maximum frequency of
    the input bands. Every band therefore spans at least one source band: rebinned
    values aggregate whole source bands, adjacent bands stay statistically
    independent, and a tone narrower than the band spacing lands compactly at every
    frequency. The axis is linear at the low end and transitions to the logarithmic
    spacing where the musical interval outgrows the source resolution.

    Args:
        bands: Original uniformly-spaced frequency band edges.
        cutoff: Cutoff frequency. The first generated edge.
        bins_per_octave: Number of bands per octave in the logarithmic region.

    Returns:
        Array of strictly increasing frequency edges from the cutoff to the maximum
        band frequency.

    Raises:
        TypeError: If bands is not an Array.
        ValueError: If bands has less than two elements.
        ValueError: If bands is not one-dimensional.
        ValueError: If bins_per_octave is not a positive integer.
        ValueError: If cutoff frequency is greater than or equal to the maximum band frequency.
    """
    if not isinstance(bands, ArrayClasses):
        raise TypeError("bands must be an Array")

    if bands.size < 2:
        raise ValueError("bands array must contain at least two elements")

    if bands.ndim != 1:
        raise ValueError("bands array must be one-dimensional")

    if bins_per_octave < 1:
        raise ValueError("bins_per_octave must be a positive integer")

    if cutoff >= bands[-1]:
        raise ValueError("cutoff frequency must be less than the maximum band frequency")

    module = get_array_module(bands)
    resolution = float(bands[1] - bands[0])
    edges = _resolution_floored_edges(float(bands[-1]), float(cutoff), bins_per_octave, resolution)
    return module.asarray(edges, dtype=bands.dtype)
