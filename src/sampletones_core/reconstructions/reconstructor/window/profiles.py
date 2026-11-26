from dataclasses import dataclass
from functools import lru_cache
from typing import Final, List, Self, Sequence, Tuple, assert_never

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones_core.fft import Window
from sampletones_core.fft.cqt.frequencies import calculate_cqt_frequencies
from sampletones_core.fft.cqt.geometry import calculate_wavelet_lengths
from sampletones_core.fft.cqt.kernel import window_envelope
from sampletones_core.fft.cqt.transform import FRAMES_WINDOW, wavelet_positions
from sampletones_core.fft.layers import analysis_layers

CACHED_PROFILES: Final[int] = 4


@dataclass(frozen=True)
class BinWindow:
    """One bin's analysis window laid over the frames around the frame it reads.

    A channel holds what it plays for a whole frame, so each sample the window weighs sounds what
    the frame it falls within plays. That frame's offset from the frame read is the floor of the
    sample's position over the frame length, the position counted in samples from the start of the
    frame read, which holds the positions from zero to one short of the frame length.

    The window's shares stand on the frames from ``-reach`` to ``reach`` for any reach at least its
    own, so bins whose windows reach differently fill one table.

    Attributes:
        offsets: The offset of the frame each sample falls within, from the frame read.
        weights: The window's weight on each sample.
    """

    offsets: np.ndarray
    weights: np.ndarray

    @classmethod
    def placed(cls, positions: np.ndarray, weights: np.ndarray, frame_length: int) -> Self:
        """The window weighing its samples by ``weights``, its samples at ``positions`` from the frame's start."""
        return cls(offsets=np.floor(positions / frame_length).astype(np.int64), weights=weights)

    @property
    def reach(self) -> int:
        """The farthest frame the window reaches, in frames on either side."""
        return int(np.abs(self.offsets).max())

    def amplitude_shares(self, reach: int) -> np.ndarray:
        """The share of the window's weight on each frame from ``-reach`` to ``reach``."""
        return self._shares(self.weights, reach)

    def energy_shares(self, reach: int) -> np.ndarray:
        """The share of the window's squared weight on each frame from ``-reach`` to ``reach``."""
        return self._shares(np.square(self.weights), reach)

    def _shares(self, weights: np.ndarray, reach: int) -> np.ndarray:
        """The share of the summed ``weights`` the samples of each frame from ``-reach`` to ``reach`` hold."""
        return np.asarray(np.bincount(self.offsets + reach, weights=weights, minlength=2 * reach + 1) / weights.sum())


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

    @classmethod
    def of(cls, windows: Sequence[BinWindow]) -> Self:
        """The profiles of bins reading through ``windows``, one window per bin.

        Every bin's shares stand on the offsets the farthest-reaching window spans, so a bin whose
        window reaches less holds zero on the frames beyond it.
        """
        reach = max(window.reach for window in windows)
        amplitude = np.zeros((2 * reach + 1, len(windows)))
        energy = np.zeros_like(amplitude)
        for index, window in enumerate(windows):
            amplitude[:, index] = window.amplitude_shares(reach)
            energy[:, index] = window.energy_shares(reach)

        return cls(amplitude=amplitude, energy=energy, reach=reach)

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


def frame_profiles(config: Config, window: Window, sizes: Sequence[int]) -> FrameProfiles:
    """The frame profiles of the feature ``config`` analyzes with, every analysis layer's bins in order.

    The constant-Q feature reads each bin through a wavelet of its own length, standing where the
    transform places it around the middle of the frame. The windowed features read every bin through
    one tapered window starting where the layer's window places it. A frame read by several spectrum
    methods stacks their bins (``analysis_layers``), so its profiles stack each method's.

    Args:
        config: The configuration whose spectrum methods the frames are read with.
        window: The analysis window of the library's own method, which sets the frame length.
        sizes: How many bins each analysis layer's reading holds, in the order the frame's feature
            stacks them.

    Returns:
        The profiles of every bin.
    """
    layers = analysis_layers(config)
    windows = (window, *(layer.window for layer in layers[1:]))
    return FrameProfiles.of(
        [
            bin_window
            for layer, layer_window, bins in zip(layers, windows, sizes, strict=True)
            for bin_window in _layer_windows(layer.config, layer_window, bins)
        ]
    )


def _layer_windows(config: Config, window: Window, bins: int) -> Tuple[BinWindow, ...]:
    """Each bin's window over the frames, for the bins one spectrum method reads."""
    method = config.library.spectrum_method
    match method:
        case SpectrumMethod.CQT:
            return _constant_q_windows(config.library.sample_rate, window.frame_length, bins)
        case SpectrumMethod.FFT | SpectrumMethod.LOG_SPACED_FFT:
            envelope = tuple(float(weight) for weight in window.envelope)
            return (_tapered_window(envelope, window.left_offset, window.frame_length),) * bins
        case _:
            assert_never(method)


@lru_cache(maxsize=CACHED_PROFILES)
def _constant_q_windows(sample_rate: int, frame_length: int, bins: int) -> Tuple[BinWindow, ...]:
    """Each bin's wavelet over the frames, on the bins the constant-Q feature reads.

    The wavelets depend on the configuration alone, so a process lays them once for each
    configuration it converts with.
    """
    return tuple(constant_q_windows(sample_rate, frame_length, bins))


def constant_q_windows(sample_rate: int, frame_length: int, bins: int) -> List[BinWindow]:
    """Each bin's wavelet laid over the frames around the frame it reads, one window per bin.

    The kernel frame the transform lays every wavelet in is as long as the longest wavelet, the
    lowest bin's.
    """
    frequencies = calculate_cqt_frequencies(bins, CQT_CUTOFF_FREQUENCY, BINS_PER_OCTAVE)
    lengths = calculate_wavelet_lengths(frequencies, sample_rate, BINS_PER_OCTAVE).astype(int)
    kernel_length = int(lengths.max())
    return [_wavelet(int(length), kernel_length, frame_length) for length in lengths]


def _wavelet(length: int, kernel_length: int, frame_length: int) -> BinWindow:
    """A bin's wavelet of ``length`` samples, where the transform places it around the frame it reads.

    Its samples stand at the transform's ``wavelet_positions`` within a kernel frame of
    ``kernel_length`` samples. The wavelet's envelope is the one the constant-Q transform weighs each
    frame's column by.
    """
    positions = wavelet_positions(length, frame_length=kernel_length, hop_length=frame_length)
    return BinWindow.placed(positions, window_envelope(FRAMES_WINDOW, length), frame_length)


@lru_cache(maxsize=CACHED_PROFILES)
def _tapered_window(envelope: Tuple[float, ...], left_offset: int, frame_length: int) -> BinWindow:
    """The one tapered window every bin of a windowed feature reads through.

    The window's ``envelope`` arrives as a tuple so the cache can key on it. Its first sample lies
    ``left_offset`` samples from the frame's start.
    """
    weights = np.asarray(envelope, dtype=np.float64)
    return BinWindow.placed(left_offset + np.arange(weights.shape[0]), weights, frame_length)
