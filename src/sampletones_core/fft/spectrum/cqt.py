from typing import List, Optional

import numpy as np

from sampletones_core.audio import validate_audio_array
from sampletones_core.constants.spectrum import (
    BINS_PER_OCTAVE,
    CQT_CUTOFF_FREQUENCY,
)
from sampletones_core.structures.histogram import Histogram

from ..cqt.frequencies import calculate_cqt_frequencies, convert_midpoints_to_edges
from ..cqt.normalization import normalize_cqt_energy
from ..cqt.transform import calculate_cqt, calculate_cqt_frames
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

    frequencies = calculate_cqt_frequencies(
        n_bins,
        cutoff,
        bins_per_octave,
    )

    energy: np.ndarray = np.mean(np.square(np.abs(cqt)), axis=1)
    energy_scaled = normalize_cqt_energy(energy, frequencies, sample_rate, bins_per_octave)
    bands: np.ndarray = convert_midpoints_to_edges(frequencies)
    return Histogram(edges=bands.astype(np.float32), values=energy_scaled.astype(np.float32))


def calculate_cqt_spectrum_columns(
    audio: np.ndarray,
    sample_rate: int,
    hop_length: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    bins_per_octave: int = BINS_PER_OCTAVE,
    n_bins: Optional[int] = None,
) -> List[Histogram]:
    """
    Compute one CQT power-spectrum histogram per frame of a whole signal.

    Shares the bins, energy normalization and edges of calculate_cqt_spectrum, but
    returns a per-frame column instead of a single aggregated frame. The matching
    target and the candidate references are both built from this function so they
    share an identical feature-extraction contract and stay directly comparable
    bin-by-bin.

    The transform centers column ``i`` on sample ``i * hop_length``, whereas the matching
    pipeline indexes a fragment by its center (the FFT path analyses a window centered on the
    frame). The signal is therefore advanced by half a hop before transforming, so column ``i``
    represents the frame centered on ``(i + 0.5) * hop_length`` and the per-frame timing matches
    the FFT path exactly.

    Args:
        audio: Input audio as a numpy array.
        sample_rate: Sampling rate in Hz.
        hop_length: Samples between consecutive frames (the frame length).
        cutoff: Minimum frequency in Hz.
        bins_per_octave: Number of bins per octave.
        n_bins: Number of CQT bins. If None, automatically calculated to reach Nyquist.

    Returns:
        One Histogram per frame, all sharing the same log-spaced edges.
    """
    validate_audio_array(audio)
    n_bins = n_bins or calculate_n_bins(sample_rate, cutoff, bins_per_octave)
    centered_audio = audio[hop_length // 2 :]
    cqt = calculate_cqt_frames(centered_audio, sample_rate, hop_length, cutoff, n_bins, bins_per_octave)
    frequencies = calculate_cqt_frequencies(n_bins, cutoff, bins_per_octave)
    energy: np.ndarray = np.square(np.abs(cqt))
    energy_scaled = normalize_cqt_energy(energy, frequencies, sample_rate, bins_per_octave)
    edges: np.ndarray = convert_midpoints_to_edges(frequencies).astype(np.float32)
    return [
        Histogram(edges=edges, values=energy_scaled[:, frame].astype(np.float32))
        for frame in range(energy_scaled.shape[1])
    ]
