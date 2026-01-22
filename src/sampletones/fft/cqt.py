import librosa
import numpy as np

from sampletones.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY

from .utils import rectangle_window


def calculate_cqt(
    audio: np.ndarray,
    sample_rate: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    n_bins: int = 347,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
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
