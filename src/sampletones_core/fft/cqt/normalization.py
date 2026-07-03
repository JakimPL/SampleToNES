import numpy as np

from sampletones_core.constants.spectrum import BINS_PER_OCTAVE

from .geometry import calculate_wavelet_lengths


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
    lengths = calculate_wavelet_lengths(frequencies, sample_rate, bins_per_octave)
    broadcast_shape = [1] * energy.ndim
    broadcast_shape[0] = lengths.shape[0]
    energy_scaled: np.ndarray = 2.0 * energy / lengths.reshape(broadcast_shape)
    return energy_scaled
