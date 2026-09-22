from typing import AbstractSet, Callable, Dict, Final, Mapping, Sequence, Tuple

from sampletones_application.logic.reconstruction.listening import offered_channels
from sampletones_application.view_model.shared.ownership import (
    OwnershipLaneViewModel,
    OwnershipRunViewModel,
)
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.ownership import heard_frame, owner_runs

DISTINGUISHABLE_OWNERS: Final[int] = 2

HeardOn = Callable[[ChannelName], AbstractSet[int]]


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


def recording_names(stems_data: StemsData) -> Tuple[str, ...]:
    """The recordings a document names, in the order the record paints them.

    The name standing in a given place is the recording standing at that place on the record, which
    is where every surface reads its color from, so a list of these names and a column of swatches
    beside them agree. A record whose recordings and entries fail to answer for each other names
    nothing, a name worth reading being one that sits where its color does.

    Args:
        stems_data: The record the document carries.

    Returns:
        Tuple[str, ...]: One name per recording, in record order.
    """
    positions = record_positions(stems_data)
    sources = stems_data.sources_by_id
    if sources.keys() != positions.keys():
        return ()

    return tuple(sources[stem_id].name for stem_id in sorted(positions, key=lambda stem_id: positions[stem_id]))


def tells_owners_apart(stems_data: StemsData) -> bool:
    """Whether the document holds owners a color has something to tell apart.

    An owner is a recording the record names, or the row the frames a reader wrote gather under:
    both take a color of their own and both stand on the stems card, so a document holding one
    recording and an edit beside it has two owners to tell apart.

    Args:
        stems_data: The record the document carries.

    Returns:
        bool: True where two or more owners stand on the record.
    """
    return len(offered_channels(stems_data)) >= DISTINGUISHABLE_OWNERS


def ownership_lanes(
    stems_data: StemsData,
    assignments: Mapping[ChannelName, Sequence[int]],
    heard_on: HeardOn,
) -> Dict[ChannelName, OwnershipLaneViewModel]:
    """A lane per channel of ``assignments``, each divided into the stretches its owners hold.

    Each surface states its own reading as the assignments it passes — which channels stand, and
    how far each lane runs — so the rule dividing a channel into stretches is written once and
    the ribbon under the waveform and the band under an instrument's bars agree by construction.
    Whether a lane is worth drawing at all is the caller's own question: a surface with room for
    only one reading, such as an instrument's bars, asks ``tells_owners_apart`` first and skips
    this call where a document answering to a single owner has nothing to tell apart; a surface
    reading every channel of a document at once, such as the waveform's ribbon, has a plainer
    question to answer instead — whether a channel plays — and takes a lane for every one that
    does.

    Args:
        stems_data: The record the document carries.
        assignments: The stem holding each frame, per channel the surface draws.
        heard_on: The recordings the reader hears on a channel.

    Returns:
        Dict[ChannelName, OwnershipLaneViewModel]: One lane per channel given, in that order.
    """
    positions = record_positions(stems_data)
    return {
        channel_name: _ownership_lane(channel_name, stem_ids, positions, heard_on(channel_name))
        for channel_name, stem_ids in assignments.items()
    }


def _ownership_lane(
    channel_name: ChannelName,
    stem_ids: Sequence[int],
    positions: Mapping[int, int],
    heard: AbstractSet[int],
) -> OwnershipLaneViewModel:
    """One channel's lane: the stretches it divides into, each under the recording holding it.

    A stretch keeps the recording holding it and says whether the reader hears it there, so
    the lane names an owner wherever the record does and shows the reader's choice on top of it.
    A resting stretch answers to no recording, so it takes no stretch of its own and leaves the
    ground of whatever surface draws the lane showing through.
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
            if run.stem_id != RESTING_STEM_ID
        ),
    )
