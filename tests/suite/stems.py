from typing import List, Mapping, Sequence

from sampletones_core.constants.algorithm import DEFAULT_STEMS_CHANNEL_CAP
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData


def single_entry_stems_data(
    channels: List[ChannelName],
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
) -> StemsData:
    """The single-entry record for ``channels``, stem 0 owning each frame that plays."""
    assignments = [
        ChannelAssignment(channel_name=channel_name, stem_ids=[0] * len(stream))
        for channel_name, stream in instructions.items()
        if stream
    ]
    return StemsData.single_entry(
        channels,
        assignments,
    )
