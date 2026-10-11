from typing import AbstractSet, Callable, Dict, Final, Mapping, Sequence, Tuple

from sampletones_application.logic.reconstruction.listening import offered_channels
from sampletones_application.view_model.shared.ownership import (
    OwnershipLaneViewModel,
    OwnershipRunViewModel,
)
from sampletones_application.view_model.shared.recording import NamedRecordingViewModel
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.ownership import OwnerRun, heard_frame

DISTINGUISHABLE_OWNERS: Final[int] = 2

HeardOn = Callable[[ChannelName], AbstractSet[int]]


def named_recordings(stems_data: StemsData) -> Tuple[NamedRecordingViewModel, ...]:
    """The recordings a document names, in record order, each with the id that picks its color.

    Every surface painting a recording reads its color from the id it was converted as, so a
    list of these and a column of swatches beside them agree with the stretches the ribbon draws.
    A record whose recordings and entries fail to answer for each other names nothing, a name
    worth reading being one that sits where its color does.

    Args:
        stems_data: The record the document carries.

    Returns:
        Tuple[NamedRecordingViewModel, ...]: One per recording, in record order.
    """
    sources = stems_data.sources_by_id
    entries = stems_data.config.entries
    if sources.keys() != stems_data.config.entries_by_id.keys():
        return ()

    return tuple(NamedRecordingViewModel(stem_id=entry.id, name=sources[entry.id].name) for entry in entries)


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
    runs: Mapping[ChannelName, Sequence[OwnerRun]],
    heard_on: HeardOn,
) -> Dict[ChannelName, OwnershipLaneViewModel]:
    """A lane per channel of ``runs``, each divided into the stretches its owners hold.

    Each surface states its own reading as the stretches it passes — which channels stand, and
    how far each lane runs — so the rule painting a stretch is written once and the ribbon under
    the waveform and the band under an instrument's bars agree by construction. The stretches
    themselves are the record's own (``StemsData.owner_runs_by_channel``), read from its frames
    once and shared by every surface. Whether a lane is worth drawing at all is the caller's own
    question: a surface with room for only one reading, such as an instrument's bars, asks
    ``tells_owners_apart`` first and skips this call where a document answering to a single owner
    has nothing to tell apart; a surface reading every channel of a document at once, such as the
    waveform's ribbon, has a plainer question to answer instead — whether a channel plays — and
    takes a lane for every one that does.

    Args:
        runs: The stretches each channel divides into, per channel the surface draws.
        heard_on: The recordings the reader hears on a channel.

    Returns:
        Dict[ChannelName, OwnershipLaneViewModel]: One lane per channel given, in that order.
    """
    return {
        channel_name: _ownership_lane(channel_name, channel_runs, heard_on(channel_name))
        for channel_name, channel_runs in runs.items()
    }


def _ownership_lane(
    channel_name: ChannelName,
    runs: Sequence[OwnerRun],
    heard: AbstractSet[int],
) -> OwnershipLaneViewModel:
    """One channel's lane: its stretches, each under the recording holding it.

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
                heard=heard_frame(run.stem_id, heard),
            )
            for run in runs
            if run.stem_id != RESTING_STEM_ID
        ),
    )
