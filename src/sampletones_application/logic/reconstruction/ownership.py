from typing import AbstractSet, Dict, Final, Mapping, Sequence

from sampletones_application.view_model.shared.ownership import (
    OwnershipLaneViewModel,
    OwnershipRunViewModel,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.ownership import heard_frame, owner_runs

DISTINGUISHABLE_RECORDINGS: Final[int] = 2


def record_positions(stems_data: StemsData) -> Dict[int, int]:
    """Where each recording's entry stands on the record, which is what picks its color.

    Every surface painting a recording reads this one ordering, so a stretch under the waveform,
    a stretch under an instrument's bars and the swatch beside a name are drawn in the same color.

    Args:
        stems_data: The record the document carries.

    Returns:
        Dict[int, int]: The place each recording's entry stands at, by stem id.
    """
    return {entry.id: index for index, entry in enumerate(stems_data.config.entries)}


def tells_recordings_apart(stems_data: StemsData) -> bool:
    """Whether the document holds recordings a color has something to tell apart.

    Args:
        stems_data: The record the document carries.

    Returns:
        bool: True where two or more recordings stand on the record.
    """
    return len(record_positions(stems_data)) >= DISTINGUISHABLE_RECORDINGS


def ownership_lane(
    channel_name: ChannelName,
    stem_ids: Sequence[int],
    positions: Mapping[int, int],
    heard: AbstractSet[int],
) -> OwnershipLaneViewModel:
    """One channel's lane: the stretches it divides into, each under the recording heard on it.

    A stretch keeps the recording holding it and says whether the reader hears it there, so
    the lane names an owner wherever the record does and shows the reader's choice on top of it.

    Args:
        channel_name: The channel the lane stands for.
        stem_ids: The stem holding each frame, as far as the lane runs.
        positions: Where each recording's entry stands on the record.
        heard: The recordings the reader hears on this channel.

    Returns:
        OwnershipLaneViewModel: The channel's stretches, in frame order.
    """
    return OwnershipLaneViewModel(
        channel_name=channel_name,
        runs=tuple(
            OwnershipRunViewModel(
                start_frame=run.start,
                end_frame=run.end,
                stem_id=run.stem_id,
                position=positions.get(run.stem_id, 0),
                heard=heard_frame(run.stem_id, heard),
            )
            for run in owner_runs(stem_ids)
        ),
    )
