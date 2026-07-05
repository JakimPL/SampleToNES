import numpy as np

from sampletones_core.constants.spectrum import BINS_PER_OCTAVE


def quality_factor(bins_per_octave: int = BINS_PER_OCTAVE) -> float:
    """
    Constant-Q quality factor: the ratio of a bin's center frequency to its bandwidth.

    Adjacent logarithmically-spaced bins differ by a factor of ``2 ** (1 / bins_per_octave)``;
    holding that relative bandwidth constant across the spectrum fixes
    ``Q = 1 / (2 ** (1 / bins_per_octave) - 1)``. Q equals the number of cycles a bin's wavelet
    spans, which sets how much signal the bin needs to resolve.

    Args:
        bins_per_octave: Number of bins per octave.

    Returns:
        The quality factor Q.
    """
    return 1.0 / (2 ** (1 / bins_per_octave) - 1)


def calculate_wavelet_lengths(
    frequencies: np.ndarray,
    sample_rate: int,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
    """
    Length in samples of each bin's constant-Q wavelet.

    A bin centered at ``f`` spans Q cycles, so its wavelet occupies ``Q * sample_rate / f``
    samples, rounded up. This is the amount of signal the bin needs to reach constant-Q
    resolution, and the per-bin factor that normalizes raw CQT energy across bins.

    Args:
        frequencies: Center frequencies of the bins in Hz.
        sample_rate: Sampling rate in Hz.
        bins_per_octave: Number of bins per octave.

    Returns:
        Wavelet length in samples for each bin, same shape as ``frequencies``.
    """
    lengths: np.ndarray = np.ceil(quality_factor(bins_per_octave) * sample_rate / frequencies)
    return lengths


def reliable_frequency_floor(
    sample_rate: int,
    signal_length: int,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> float:
    """
    Lowest center frequency a signal of ``signal_length`` samples resolves at constant Q.

    Inverting the wavelet-length relation ``Q * sample_rate / f = signal_length`` gives
    ``f = Q * sample_rate / signal_length``: a bin's full wavelet fits within the signal at or
    above this frequency. Content below it is measured over less than one wavelet, so its energy
    is under-resolved and the low bins report a smeared, under-read estimate.

    Args:
        sample_rate: Sampling rate in Hz.
        signal_length: Number of samples available for the transform.
        bins_per_octave: Number of bins per octave.

    Returns:
        The lowest reliably-resolved frequency in Hz.
    """
    return quality_factor(bins_per_octave) * sample_rate / signal_length


def resolvable_bins(
    frequencies: np.ndarray,
    sample_rate: int,
    signal_length: int,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
    """
    Boolean mask marking bins whose constant-Q wavelet fits within ``signal_length`` samples.

    A bin is resolvable when its wavelet length is at most the signal length, reusing the same
    per-bin wavelet lengths that normalize CQT energy so the reliability boundary lands exactly
    on the normalization boundary. Lower-frequency bins span more than the available signal and
    hold an under-resolved estimate.

    Args:
        frequencies: Center frequencies of the bins in Hz.
        sample_rate: Sampling rate in Hz.
        signal_length: Number of samples available for the transform.
        bins_per_octave: Number of bins per octave.

    Returns:
        Boolean mask, ``True`` where the bin is resolvable, same shape as ``frequencies``.
    """
    mask: np.ndarray = calculate_wavelet_lengths(frequencies, sample_rate, bins_per_octave) <= signal_length
    return mask
