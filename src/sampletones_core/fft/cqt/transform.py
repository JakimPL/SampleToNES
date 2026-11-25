from typing import Final, Optional

import numpy as np

from sampletones_core.constants.enums import CQTWindow
from sampletones_core.constants.spectrum import (
    BINS_PER_OCTAVE,
    CQT_CUTOFF_FREQUENCY,
)
from sampletones_shared.array import to_numpy, xp
from sampletones_shared.types.array import Array

from ..utils import calculate_n_bins
from .kernel import CQTKernel, build_cqt_kernel, wavelet_start

MAX_GATHERED_SAMPLES: Final[int] = 1 << 24
FRAMES_WINDOW: Final[CQTWindow] = CQTWindow.HANN
HOP_ALIGNED_OFFSET: Final[int] = 0


def leading_padding(frame_length: int) -> int:
    """The silence ahead of the audio: half a kernel frame of ``frame_length`` samples.

    A kernel frame starting ``s`` samples into the padded signal then centers on the audio's sample ``s``.
    """
    return frame_length // 2


def column_offset(hop_length: int) -> int:
    """The sample the first frame column centers on: half a hop into the audio.

    Column ``i`` then centers on the middle of frame ``i``, the samples from ``i * hop_length`` to one
    short of ``(i + 1) * hop_length``.
    """
    return hop_length // 2


def wavelet_positions(length: int, *, frame_length: int, hop_length: int) -> np.ndarray:
    """Where each sample of a wavelet of ``length`` samples falls, counted from the start of the frame
    its frame column reads.

    Column ``i`` reads the kernel frame starting ``i * hop_length + column_offset(hop_length)`` samples
    into the padded signal, which holds ``leading_padding(frame_length)`` samples of silence ahead of the
    audio. The wavelet starts ``wavelet_start(frame_length, length)`` samples into that kernel frame.

    Args:
        length: The wavelet's length in samples.
        frame_length: The kernel frame's length, the longest wavelet's.
        hop_length: Samples between consecutive columns, the frame length.

    Returns:
        np.ndarray: The position of each of the wavelet's samples, in samples from the frame's start.
    """
    first = column_offset(hop_length) - leading_padding(frame_length) + wavelet_start(frame_length, length)
    positions: np.ndarray = first + np.arange(length)
    return positions


def _padded_signal(audio: np.ndarray, frame_length: int, offset: int) -> Array:
    """``audio`` on the compute device, with ``leading_padding(frame_length)`` samples of silence ahead of it.

    The silence after the audio holds the rest of the kernel frame around the last column, wherever
    ``offset`` moves the columns' centers.
    """
    left = leading_padding(frame_length)
    right = frame_length - left + offset
    device_audio: Array = xp.asarray(audio, dtype=xp.complex64)
    padded: Array = xp.concatenate(
        [xp.zeros(left, dtype=xp.complex64), device_audio, xp.zeros(right, dtype=xp.complex64)]
    )
    return padded


def _framed_columns(
    padded: Array,
    frame_length: int,
    hop_length: int,
    offset: int,
    first: int,
    count: int,
) -> Array:
    """Stack ``count`` kernel frames of the padded signal, one column per hop from column ``first``.

    Column ``i`` holds the kernel frame centered on the audio's sample ``i * hop_length + offset``.
    """
    starts = (xp.arange(count) + first) * hop_length + offset
    indices = starts[:, None] + xp.arange(frame_length)[None, :]
    framed: Array = padded[indices].T
    return framed


def _transform(audio: np.ndarray, kernel: CQTKernel, hop_length: int, offset: int) -> np.ndarray:
    """Correlates the kernel with the frames of ``audio`` centered on sample ``offset`` and every hop after it.

    A column stands on each center from ``offset`` to the audio's end, and on ``offset`` itself where the
    audio ends before it. The audio reads as silence before its first sample and after its last.

    Every frame spans the lowest bin's whole wavelet, so the frames are gathered a block of columns
    at a time, each block holding at most ``MAX_GATHERED_SAMPLES`` samples. That keeps the memory a
    recording takes to one block, however long the recording runs.
    """
    padded = _padded_signal(audio, kernel.frame_length, offset)
    frame_count = 1 + max(len(audio) - offset, 0) // hop_length
    block = max(1, MAX_GATHERED_SAMPLES // kernel.frame_length)
    columns = [
        kernel.matrix
        @ _framed_columns(padded, kernel.frame_length, hop_length, offset, first, min(block, frame_count - first))
        for first in range(0, frame_count, block)
    ]
    coefficients: Array = xp.concatenate(columns, axis=1)
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
    return _transform(audio, kernel, hop_length, HOP_ALIGNED_OFFSET)


def calculate_cqt_frames(
    audio: np.ndarray,
    sample_rate: int,
    hop_length: int,
    offset: int,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    n_bins: Optional[int] = None,
    bins_per_octave: int = BINS_PER_OCTAVE,
) -> np.ndarray:
    """
    Compute the Constant-Q Transform of a whole signal, one column per frame.

    Correlates the signal with a Hann-windowed constant-Q kernel at each hop, centering column
    ``i`` on sample ``i * hop_length + offset``. Computing over the whole signal keeps each frame's
    energy aligned to its own time position while the long low-frequency wavelets still see the
    surrounding context. The audio reads as silence before its first sample and after its last.

    Args:
        audio: Input audio signal array.
        sample_rate: Sampling rate in Hz.
        hop_length: Samples between consecutive columns (the frame length).
        offset: The sample the first column centers on.
        cutoff: Minimum frequency in Hz.
        n_bins: Number of frequency bins. If None, calculated automatically.
        bins_per_octave: Number of bins per octave.

    Returns:
        Complex CQT coefficients, shape (n_bins, n_frames).
    """
    n_bins = n_bins or calculate_n_bins(sample_rate, cutoff, bins_per_octave)
    kernel = build_cqt_kernel(sample_rate, n_bins, cutoff, bins_per_octave, FRAMES_WINDOW)
    return _transform(audio, kernel, hop_length, offset)
