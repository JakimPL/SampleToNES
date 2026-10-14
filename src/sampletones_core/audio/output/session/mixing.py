from typing import Sequence

import numpy as np

from sampletones_core.audio.mixing import mix
from sampletones_core.audio.processing import clip_audio_inplace, silence


def mixed_block(fills: Sequence[np.ndarray], frames: int) -> np.ndarray:
    """One block for the device: every playback's samples summed and held within full scale.

    A playback whose sound ran out partway through the block leaves the rest of the block silent. A sum past
    full scale, such as the song at a boosted master gain, is clipped, and that clipping is the audible cost
    of the boost.

    Args:
        fills: Each playback's samples for the block, at most ``frames`` long.
        frames: The length of the block.
    """
    block = silence(frames)
    if not fills:
        return block

    block[:] = mix([block, *fills])
    return clip_audio_inplace(block)
