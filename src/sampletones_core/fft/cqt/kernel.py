from dataclasses import dataclass
from functools import lru_cache
from typing import assert_never

import numpy as np

from sampletones_core.constants.enums import CQTWindow
from sampletones_shared.array import xp
from sampletones_shared.types.array import Array

from .frequencies import calculate_cqt_frequencies
from .geometry import calculate_wavelet_lengths


def _window_envelope(window: CQTWindow, length: int) -> np.ndarray:
    """Real analysis envelope of ``length`` samples.

    The rectangular envelope is uniform; the Hann envelope uses the periodic form
    ``0.5 - 0.5*cos(2*pi*n/length)`` so consecutive frames tile without a seam.
    """
    match window:
        case CQTWindow.RECTANGULAR:
            return np.ones(length, dtype=np.float64)
        case CQTWindow.HANN:
            return 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(length) / length)
        case _:
            assert_never(window)


@dataclass(frozen=True)
class CQTKernel:
    """
    Precomputed constant-Q analysis operator: one conjugated, ``sqrt(N_k)``-scaled,
    L1-normalized wavelet per row. The forward transform of a stack of centered frames is
    ``matrix @ frames``. The scaling makes a unit-amplitude tone at a bin's center frequency
    produce ``|coefficient|**2 == N_k``, so dividing the energy by ``N_k`` (see
    ``normalize_cqt_energy``) yields the constant, bin-comparable magnitude of Brown's
    ``1/N_k`` normalization.
    """

    matrix: Array
    frame_length: int


@lru_cache(maxsize=8)
def build_cqt_kernel(
    sample_rate: int,
    n_bins: int,
    cutoff: float,
    bins_per_octave: int,
    window: CQTWindow,
) -> CQTKernel:
    """
    Build (and cache on the compute device) the constant-Q kernel for one configuration.

    Each row is the wavelet ``envelope[n] * exp(-2*pi*i * f_k * n / sample_rate)`` centered in a
    ``frame_length``-sample window (``frame_length`` = the longest wavelet, at ``cutoff``), divided
    by its L1 norm and multiplied by ``sqrt(N_k)``. Conjugating the analysis exponential turns the
    matmul into a correlation, so ``matrix @ frames`` gives the constant-Q coefficients directly.
    The kernel depends only on the configuration, so it is built once and reused across signals.

    Args:
        sample_rate: Sampling rate in Hz.
        n_bins: Number of frequency bins.
        cutoff: Minimum (lowest-bin) frequency in Hz.
        bins_per_octave: Number of bins per octave.
        window: Analysis envelope to apply to each wavelet.

    Returns:
        A ``CQTKernel`` whose ``matrix`` lives on the active array backend.
    """
    frequencies = calculate_cqt_frequencies(n_bins, cutoff, bins_per_octave)
    lengths = calculate_wavelet_lengths(frequencies, sample_rate, bins_per_octave).astype(int)
    frame_length = int(lengths.max())

    matrix = np.zeros((n_bins, frame_length), dtype=np.complex64)
    for index in range(n_bins):
        length = int(lengths[index])
        start = (frame_length - length) // 2
        envelope = _window_envelope(window, length)
        centered = np.arange(length) - (length - 1) / 2.0
        wavelet = envelope * np.exp(-2j * np.pi * frequencies[index] * centered / sample_rate)
        matrix[index, start : start + length] = wavelet / envelope.sum() * np.sqrt(length)

    return CQTKernel(matrix=xp.asarray(matrix), frame_length=frame_length)
