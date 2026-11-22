from dataclasses import dataclass
from functools import lru_cache
from typing import List, Tuple, assert_never

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import CQTWindow, SpectrumMethod
from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones_core.fft import Window
from sampletones_core.fft.cqt.frequencies import calculate_cqt_frequencies
from sampletones_core.fft.cqt.geometry import calculate_wavelet_lengths
from sampletones_core.fft.cqt.kernel import window_envelope


@dataclass(frozen=True)
class FrameProfiles:
    """How much of each bin's analysis window falls on each frame around the frame it reads.

    A bin of a frame's feature reads the signal through a window that may span the frames on either
    side. A note held over several frames keeps its phase, so it reaches the bin by the share of the
    window's weight its frames hold, in amplitude. Noise reaches the bin by the share of the window's
    squared weight, in power. A note held through the whole window reaches it whole either way.

    Attributes:
        amplitude: Each bin's share of window weight on each frame, one row per offset from
            ``-reach`` to ``reach``; every column sums to one.
        energy: Each bin's share of squared window weight on each frame, shaped alike.
        reach: The farthest any bin's window reaches, in frames on either side.
    """

    amplitude: np.ndarray
    energy: np.ndarray
    reach: int

    @property
    def own_amplitude(self) -> np.ndarray:
        """Each bin's share of window weight on the frame it reads."""
        return np.asarray(self.amplitude[self.reach])

    @property
    def own_energy(self) -> np.ndarray:
        """Each bin's share of squared window weight on the frame it reads."""
        return np.asarray(self.energy[self.reach])

    def amplitude_at(self, offset: int) -> np.ndarray:
        """Each bin's share of window weight on the frame ``offset`` frames away."""
        return np.asarray(self.amplitude[self.reach + offset])

    def energy_at(self, offset: int) -> np.ndarray:
        """Each bin's share of squared window weight on the frame ``offset`` frames away."""
        return np.asarray(self.energy[self.reach + offset])


def frame_profiles(config: Config, window: Window, bins: int) -> FrameProfiles:
    """The frame profiles of the feature ``config`` analyzes with.

    The constant-Q feature reads each bin through a Hann wavelet of its own length centered on the
    middle of the frame. The windowed features read every bin through one tapered window starting
    where ``window`` places it.

    Args:
        config: The configuration whose spectrum method the frames are read with.
        window: The analysis window, which sets the frame length and the windowed features' envelope.
        bins: How many bins a frame's feature holds.

    Returns:
        The profiles of every bin.
    """
    method = config.library.spectrum_method
    match method:
        case SpectrumMethod.CQT:
            return _constant_q_profiles(config.library.sample_rate, window.frame_length, bins)
        case SpectrumMethod.FFT | SpectrumMethod.LOG_SPACED_FFT:
            return _windowed_profiles(
                tuple(float(weight) for weight in window.envelope), window.left_offset, window.frame_length, bins
            )
        case _:
            assert_never(method)


@lru_cache(maxsize=4)
def _constant_q_profiles(sample_rate: int, frame_length: int, bins: int) -> FrameProfiles:
    """Each bin's wavelet weighed over the frames, the wavelet centered on the middle of the frame."""
    frequencies = calculate_cqt_frequencies(bins, CQT_CUTOFF_FREQUENCY, BINS_PER_OCTAVE)
    lengths = calculate_wavelet_lengths(frequencies, sample_rate, BINS_PER_OCTAVE).astype(int)
    placements: List[Tuple[np.ndarray, np.ndarray]] = []
    for length in lengths:
        centered = np.arange(length) - (length - 1) / 2.0
        offsets = np.floor((centered + frame_length / 2.0) / frame_length).astype(np.int64)
        placements.append((offsets, window_envelope(CQTWindow.HANN, int(length))))

    return _profiles(placements)


@lru_cache(maxsize=4)
def _windowed_profiles(envelope: Tuple[float, ...], left_offset: int, frame_length: int, bins: int) -> FrameProfiles:
    """One tapered window weighed over the frames, shared by every bin."""
    weights = np.asarray(envelope, dtype=np.float64)
    offsets = np.floor_divide(left_offset + np.arange(weights.shape[0]), frame_length).astype(np.int64)
    return _profiles([(offsets, weights)] * bins)


def _profiles(placements: List[Tuple[np.ndarray, np.ndarray]]) -> FrameProfiles:
    """The profiles of bins whose windows place ``weights`` on the frames ``offsets`` name."""
    reach = max(int(np.abs(offsets).max()) for offsets, _ in placements)
    amplitude = np.zeros((2 * reach + 1, len(placements)))
    energy = np.zeros_like(amplitude)
    for index, (offsets, weights) in enumerate(placements):
        amplitude[:, index] = np.bincount(offsets + reach, weights=weights, minlength=2 * reach + 1) / weights.sum()
        squared = np.square(weights)
        energy[:, index] = np.bincount(offsets + reach, weights=squared, minlength=2 * reach + 1) / squared.sum()

    return FrameProfiles(amplitude=amplitude, energy=energy, reach=reach)
