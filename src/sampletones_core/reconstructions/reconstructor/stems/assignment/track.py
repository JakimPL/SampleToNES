from typing import Dict, List, Sequence

from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.decoder.base import ChannelLattice, Lattices
from sampletones_core.reconstructions.reconstructor.matching import Column
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment


class TrackAssignment:
    """
    Gathers a recording's frame assignments into what the rest of the reconstruction reads.

    Two records grow side by side, both in frame order: the lattice each channel offers the
    decoder, and the stem that owns each of the channel's frames. Keeping them parallel is
    what lets a stem selection name the frames it sounds in.
    """

    def __init__(self, channel_names: Sequence[ChannelName]) -> None:
        self.lattices: Lattices = {channel_name: [] for channel_name in channel_names}
        self.stem_ids: Dict[ChannelName, List[int]] = {channel_name: [] for channel_name in channel_names}

    def add(self, frame_assignment: StemFrameAssignment) -> None:
        """Appends one frame: every channel in play gains its column and the stem that took it."""
        for choice in frame_assignment.choices:
            self._append(choice.channel_name, choice.stem_id, choice.column)

        for rest in frame_assignment.rests:
            self._append(rest.channel_name, RESTING_STEM_ID, rest.column)

    def drop(self, channel_name: ChannelName) -> None:
        """Releases a channel's records, leaving it out of the reconstruction being assembled."""
        del self.lattices[channel_name]
        del self.stem_ids[channel_name]

    @property
    def resting_channels(self) -> List[ChannelName]:
        """The channels that rested through every frame, which sound nothing anywhere."""
        return [
            channel_name
            for channel_name, stem_ids in self.stem_ids.items()
            if all(stem_id == RESTING_STEM_ID for stem_id in stem_ids)
        ]

    def _append(self, channel_name: ChannelName, stem_id: int, column: Column) -> None:
        lattice: ChannelLattice = self.lattices[channel_name]
        lattice.append(column)
        self.stem_ids[channel_name].append(stem_id)
