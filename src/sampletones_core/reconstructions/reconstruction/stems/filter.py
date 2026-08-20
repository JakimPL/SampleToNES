from typing import AbstractSet, Dict, Mapping

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData


def filter_approximations(
    stems_data: StemsData,
    approximations: Mapping[ChannelName, np.ndarray],
    selected_stem_ids: AbstractSet[int],
    frame_length: int,
) -> Dict[ChannelName, np.ndarray]:
    """Returns the per-channel approximations with the unselected stems' frames zeroed.

    Stem id ``i`` names frame ``i`` of its channel — the same index the channel's stored
    approximation slices hold — so a frame whose stem is unselected becomes silence while
    every other frame keeps its samples. The arrays keep their lengths, which is what
    aligns a filtered mix with the unfiltered one sample for sample. Every selected stem
    answers the original arrays, and channels the stems data names come back filtered.
    """
    filtered: Dict[ChannelName, np.ndarray] = {}
    for channel, stem_ids in stems_data.assignments_by_channel.items():
        approximation = approximations[channel]
        keep = np.isin(np.array(stem_ids, dtype=int), list(selected_stem_ids))
        masked = np.array(approximation, copy=True)
        masked[~np.repeat(keep, frame_length)] = 0
        filtered[channel] = masked

    return filtered
