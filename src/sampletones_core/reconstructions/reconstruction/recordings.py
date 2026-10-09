from typing import Tuple

import numpy as np

from sampletones_core.audio import mix_scale, read_stems, scale_stems
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction


def load_recordings(reconstruction: Reconstruction) -> Tuple[np.ndarray, ...]:
    """The recordings a document names, each at the level its conversion read it at.

    The conversion divided the whole set it read by one factor, which the record keeps, so a
    recording stays at that level once another leaves the document and across a save and a reload.
    A record stating no factor holds one recording, which its own peak scales the way its
    conversion scaled it.

    Args:
        reconstruction: The document whose recordings are read.

    Returns:
        Tuple[np.ndarray, ...]: One recording per path the document names, in entry order.

    Raises:
        FileNotFoundError: If a path names no file.
        IsADirectoryError: If a path points at a directory.
    """
    config = reconstruction.config
    general = config.general
    recordings = read_stems(reconstruction.audio_filepath, target_sample_rate=config.library.sample_rate)
    scale = reconstruction.stems_data.scale
    return scale_stems(
        recordings,
        scale=scale if scale is not None else mix_scale(recordings, normalize=general.normalize),
        quantize=general.quantize,
        quantization_levels=general.quantization_levels,
    )
