from typing import Optional

import numpy as np

from sampletones.audio import validate_audio_array
from sampletones.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones.structures.histogram import Histogram

from ..cqt import calculate_cqt, calculate_frequencies, convert_midpoints_to_edges, normalize_cqt_energy
from ..utils import calculate_n_bins


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
    validate_audio_array(audio)
    n_bins = n_bins or calculate_n_bins(sample_rate, cutoff, bins_per_octave)
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
