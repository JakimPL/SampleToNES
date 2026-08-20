from typing import Iterable, List, Sequence

import numpy as np

from sampletones_shared.utils.arrays import pad

from .processing import silence
from .validation import validate_audio_array


def common_length(tracks: Iterable[np.ndarray]) -> int:
    """The length every track reaches when they are laid over one another.

    Args:
        tracks: The waveforms to measure.

    Returns:
        int: The length of the longest track, and zero where there are none.

    Examples:
        >>> common_length([np.zeros(3), np.zeros(7)])
        7
        >>> common_length([])
        0
    """
    return max((len(track) for track in tracks), default=0)


def align(tracks: Sequence[np.ndarray], length: int) -> List[np.ndarray]:
    """Every track brought to one length, silence filling what a shorter one leaves.

    A shorter track keeps its samples and runs on in silence; a longer one ends at `length`.
    Waveforms sharing a length stack into a single array, which is what lets a set of sources
    be summed at once and stored as one another's equals.

    Args:
        tracks: The waveforms to align, each one-dimensional.
        length: The length each track reaches.

    Returns:
        List[np.ndarray]: The tracks in the order given, each one `length` samples long.

    Raises:
        TypeError: If a track is not a numpy array.
        ValueError: If a track is not one-dimensional, or if `length` is negative.

    Examples:
        >>> align([np.array([1.0, 2.0]), np.array([3.0])], 3)
        [array([1., 2., 0.]), array([3., 0., 0.])]
    """
    if length < 0:
        raise ValueError(f"Length must be at least 0, got {length}")

    for track in tracks:
        validate_audio_array(track)

    return [pad(track, 0, length) for track in tracks]


def mix(tracks: Sequence[np.ndarray]) -> np.ndarray:
    """The tracks summed into one waveform, as long as the longest of them.

    Every track carries the level it reaches the mix at — a generator bakes its channel's mixer
    weight into what it renders, and a recorded stem carries the level it was captured at — so a
    plain sum is what combines them once they share a length.

    Args:
        tracks: The waveforms to mix, each one-dimensional.

    Returns:
        np.ndarray: The mixed waveform, empty where no track sounds.

    Raises:
        TypeError: If a track is not a numpy array.
        ValueError: If a track is not one-dimensional.

    Examples:
        >>> mix([np.array([1.0, 1.0]), np.array([0.5])])
        array([1.5, 1. ], dtype=float32)
        >>> mix([])
        array([], dtype=float32)
    """
    aligned = align(tracks, common_length(tracks))
    if not aligned:
        return silence(0)

    mixed: np.ndarray = np.sum(np.array(aligned), axis=0).astype(np.float32)
    return mixed
