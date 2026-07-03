from typing import Optional

import numpy as np

from sampletones_core.constants.enums import CQTWindow
from sampletones_core.constants.spectrum import (
    BINS_PER_OCTAVE,
    CQT_CUTOFF_FREQUENCY,
)
from sampletones_shared.array import to_numpy, xp
from sampletones_shared.types.array import Array

from ..utils import calculate_n_bins
from .kernel import CQTKernel, build_cqt_kernel


def _framed_signal(audio: np.ndarray, frame_length: int, hop_length: int) -> Array:
    """Stack centered frames of ``audio`` on the compute device, one column per hop.

    ``audio`` is zero-padded by half a frame on each side so column ``t`` is centered on sample
    ``t * hop_length``; the number of columns is ``1 + len(audio) // hop_length``.
    """
    left = frame_length // 2
    right = frame_length - left
    device_audio: Array = xp.asarray(audio, dtype=xp.complex64)
    padded: Array = xp.concatenate(
        [xp.zeros(left, dtype=xp.complex64), device_audio, xp.zeros(right, dtype=xp.complex64)]
    )
    frame_count = 1 + len(audio) // hop_length
    starts = xp.arange(frame_count) * hop_length
    indices = starts[:, None] + xp.arange(frame_length)[None, :]
    framed: Array = padded[indices].T
    return framed


def _transform(audio: np.ndarray, kernel: CQTKernel, hop_length: int) -> np.ndarray:
    frames = _framed_signal(audio, kernel.frame_length, hop_length)
    coefficients: Array = kernel.matrix @ frames
    return to_numpy(coefficients)


def calculate_cqt(
    audio: np.ndarray,
    sample_rate: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    n_bins: Optional[int] = None,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
    """
    Compute the Constant-Q Transform of an audio signal as a single frame.

    Correlates the signal with a rectangular-windowed constant-Q kernel over one centered frame
    spanning the whole signal. The CQT provides logarithmically-spaced frequency bins; when
    ``n_bins`` is omitted it is chosen to cover ``cutoff`` up to the Nyquist frequency.

    Args:
        audio: Input audio signal array.
        sample_rate: Sampling rate in Hz.
        cutoff: Minimum frequency in Hz.
        n_bins: Number of frequency bins. If None, calculated automatically.
        bins_per_octave: Number of bins per octave.

    Returns:
        Complex CQT coefficients, shape (n_bins, 1) for single frame.

    Examples:
        >>> audio = np.random.randn(1024).astype(np.float32)
        >>> cqt = calculate_cqt(audio, 800, cutoff=55.0)
        >>> cqt.ndim
        2
    """
    n_bins = n_bins or calculate_n_bins(sample_rate, cutoff, bins_per_octave)
    kernel = build_cqt_kernel(sample_rate, n_bins, cutoff, bins_per_octave, CQTWindow.RECTANGULAR)
    hop_length = len(audio) + 1  # a single frame
    return _transform(audio, kernel, hop_length)


def calculate_cqt_frames(
    audio: np.ndarray,
    sample_rate: int,
    hop_length: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    n_bins: Optional[int] = None,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
    """
    Compute the Constant-Q Transform of a whole signal, one column per frame.

    Correlates the signal with a Hann-windowed constant-Q kernel at each hop, centering column
    ``i`` on sample ``i * hop_length``. Computing over the whole signal keeps each frame's energy
    aligned to its own time position while the long low-frequency wavelets still see the surrounding
    context.

    Args:
        audio: Input audio signal array.
        sample_rate: Sampling rate in Hz.
        hop_length: Samples between consecutive columns (the frame length).
        cutoff: Minimum frequency in Hz.
        n_bins: Number of frequency bins. If None, calculated automatically.
        bins_per_octave: Number of bins per octave.

    Returns:
        Complex CQT coefficients, shape (n_bins, n_frames).
    """
    n_bins = n_bins or calculate_n_bins(sample_rate, cutoff, bins_per_octave)
    kernel = build_cqt_kernel(sample_rate, n_bins, cutoff, bins_per_octave, CQTWindow.HANN)
    return _transform(audio, kernel, hop_length)
