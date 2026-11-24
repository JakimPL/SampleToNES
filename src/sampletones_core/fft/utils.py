from functools import lru_cache
from typing import Final, List, Tuple

import numpy as np

from sampletones_core.constants.spectrum import (
    BINS_PER_OCTAVE,
    CQT_CUTOFF_FREQUENCY,
)
from sampletones_shared.types.array import Array, ArrayClasses, get_array_module

CACHED_LOGARITHMIC_REGIONS: Final[int] = 128


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


def to_resolution_floored_log_bands(
    bands: Array,
    cutoff: float,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> Array:
    """
    Band edges on a logarithmic axis floored at the source resolution.

    The axis turns from the source's own grid to a musical one at the first source edge where a
    logarithmic step of `2 ** (1 / bins_per_octave)` outgrows the source band above it:

    - In the floored region below that edge, the edges are the source edges themselves, from the
      source edge at or below the cutoff. Every band there is one whole source band, so the rebinned
      values there are the source bands' own: what one source band holds stays in one band.
    - In the logarithmic region, the edges step by that factor from the turning edge up to the top
      source edge. Every step there is wider than a source band, and the rebin shares a source band
      an edge cuts between the two bands it borders, by overlap.

    Args:
        bands: Source band edges, strictly increasing.
        cutoff: The lowest frequency the axis holds. The axis starts at the source edge at or below
            it, or at the lowest source edge when the cutoff lies below it.
        bins_per_octave: Number of bands per octave in the logarithmic region.

    Returns:
        Strictly increasing band edges, in the source's dtype, from the source edge at or below the
        cutoff to the top source edge.

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
    ratio = 2.0 ** (1.0 / bins_per_octave)
    floored = _floored_edges(bands, cutoff, ratio)
    logarithmic = _logarithmic_edges(float(floored[-1]), float(bands[-1]), ratio)
    return module.concatenate([floored, module.asarray(logarithmic, dtype=bands.dtype)])


def _floored_edges(bands: Array, cutoff: float, ratio: float) -> Array:
    """
    The source edges of the floored region, read from ``bands`` itself.

    They run from the source edge at or below the cutoff to the turning edge, the first whose
    logarithmic step ``ratio`` outgrows the source band above it, or to the top source edge where
    no step outgrows its band.
    """
    module = get_array_module(bands)
    first = max(int(module.searchsorted(bands, cutoff, side="right")) - 1, 0)
    turning = first
    while turning + 1 < bands.size and float(bands[turning]) * ratio <= float(bands[turning + 1]):
        turning += 1

    floored: Array = bands[first : turning + 1]
    return floored


@lru_cache(maxsize=CACHED_LOGARITHMIC_REGIONS)
def _logarithmic_edges(start: float, maximum: float, ratio: float) -> Tuple[float, ...]:
    """
    The edges of the logarithmic region above its first edge ``start``.

    Each edge stands a factor of ``ratio`` above the one before, and the last one at ``maximum``.
    The region is empty where ``start`` is the maximum already.
    """
    edges: List[float] = []
    edge = start
    while edge < maximum:
        edge = min(maximum, edge * ratio)
        edges.append(edge)

    return tuple(edges)
