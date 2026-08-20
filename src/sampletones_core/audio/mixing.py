from typing import List

import numpy as np

from sampletones_shared.utils.arrays import pad


def mix_audios(audios: List[np.ndarray]) -> np.ndarray:
    """Sums the recordings, each padded to the longest one's length.

    A single recording is the mix itself, returned as is. A mix holds a sample for
    every position the longest recording covers, so a recording shorter than the
    others contributes silence for the rest.
    """
    if not audios:
        raise ValueError("At least one recording is required")

    if len(audios) == 1:
        return audios[0]

    max_length = max(audio.shape[0] for audio in audios)
    return sum(
        (pad(audio, 0, max_length) for audio in audios),
        np.zeros(max_length, dtype=np.float64),
    )
