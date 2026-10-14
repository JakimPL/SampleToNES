from typing import Sequence, Tuple

import numpy as np

from sampletones_core.audio.mixing import mix
from sampletones_core.audio.processing import clip_audio_inplace, silence


def mixed_block(fills: Sequence[Tuple[np.ndarray, float]], frames: int) -> np.ndarray:
    """One block for the device: every playback's samples at its gain, summed and held within full scale.

    A playback whose sound ran out partway through the block leaves the rest of the block silent. A gain above
    unity can drive the sum past full scale, so the block is clipped, and that clipping is the audible cost of
    the boost.

    Args:
        fills: Each playback's samples for the block, at most ``frames`` long, and the gain it plays at.
        frames: The length of the block.
    """
    block = silence(frames)
    if not fills:
        return block

    block[:] = mix([block, *(samples * np.float32(gain) for samples, gain in fills)])
    return clip_audio_inplace(block)
