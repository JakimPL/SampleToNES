from typing import Dict, Mapping

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection


def filter_approximations(
    stems_data: StemsData,
    approximations: Mapping[ChannelName, np.ndarray],
    selection: StemSelection,
    frame_length: int,
) -> Dict[ChannelName, np.ndarray]:
    """Returns the per-channel approximations with the unselected stems' frames zeroed.

    Stem id ``i`` names frame ``i`` of its channel — the same index the channel's stored
    approximation slices hold — so a frame whose stem is unselected on that channel becomes
    silence while every other frame keeps its samples. The selection answers each channel on
    its own, so one recording is heard on a channel and stays quiet on the next. The arrays
    keep their lengths, which is what aligns a filtered mix with the unfiltered one sample for
    sample. The mask covers the frames the stored array holds; samples past the last recorded
    frame keep their values.
    """
    filtered: Dict[ChannelName, np.ndarray] = {}
    for channel, stem_ids in stems_data.assignments_by_channel.items():
        approximation = approximations[channel]
        keep = np.isin(np.array(stem_ids, dtype=int), list(selection.stems_for(channel)))
        keep_samples = np.repeat(keep, frame_length)
        masked = np.array(approximation, copy=True)
        masked[~keep_samples[: len(masked)]] = 0
        filtered[channel] = masked

    return filtered
