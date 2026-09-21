from typing import Dict, FrozenSet, Set

from sampletones_core.constants.algorithm import AUTHORED_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection


class StemListening:
    """Which recordings of the open reconstruction a reader is listening to, channel by channel.

    One choice serves every reading of the document: the frames it admits are the frames the
    waveform draws, the envelopes the instruments panel shows, the figures measuring them, what
    playback sounds and what an export writes, and they are the frames an edit reaches. Holding
    it beside the open reconstruction is what lets those readings answer from one state.

    The choice is the reader's, so it travels across an edit rather than being remade: a channel
    a recording keeps holding frames on keeps whatever was chosen for it, and one the recording
    reaches for the first time joins heard.
    """

    def __init__(self) -> None:
        self._offered: Dict[int, FrozenSet[ChannelName]] = {}
        self._heard: Dict[int, FrozenSet[ChannelName]] = {}

    @property
    def offered(self) -> Dict[int, FrozenSet[ChannelName]]:
        """The channels each recording holds frames on, which is where its row offers a box."""
        return dict(self._offered)

    @property
    def heard(self) -> Dict[int, FrozenSet[ChannelName]]:
        """The channels each recording is heard on, as the reader has left them."""
        return dict(self._heard)

    @property
    def selection(self) -> StemSelection:
        """What the reader hears, read the way the filters ask for it.

        The card keeps the channels each recording is heard on; a filter asks each channel which
        recordings it keeps, so the selection is that map turned around.
        """
        channels: Dict[ChannelName, Set[int]] = {channel_name: set() for channel_name in ChannelName.items()}
        for stem_id, stem_channels in self._heard.items():
            for channel_name in stem_channels:
                channels[channel_name].add(stem_id)

        return StemSelection(
            channels={channel_name: frozenset(stem_ids) for channel_name, stem_ids in channels.items()}
        )

    def heard_on(self, channel_name: ChannelName) -> FrozenSet[int]:
        """The recordings heard on one channel, which is the scope an edit writes in."""
        return self.selection.stems_for(channel_name)

    def adopt(self, stems_data: StemsData) -> None:
        """Carries the reader's choice onto the record as it now stands.

        A recording appearing for the first time offers everything it holds and is heard on all
        of it, which is the same rule read against the nothing it offered before, so a freshly
        opened reconstruction is heard whole.
        """
        offered = offered_channels(stems_data)
        self._heard = {
            stem_id: (self._heard.get(stem_id, frozenset()) & channels)
            | (channels - self._offered.get(stem_id, frozenset()))
            for stem_id, channels in offered.items()
        }
        self._offered = offered

    def set_channels(self, stem_id: int, channels: FrozenSet[ChannelName]) -> None:
        """Takes the channels one recording is heard on, as a box on its row leaves them."""
        self._heard[stem_id] = channels

    def release(self) -> None:
        """Lets go of the choice, which is what closing the reconstruction it describes does."""
        self._offered = {}
        self._heard = {}


def offered_channels(stems_data: StemsData) -> Dict[int, FrozenSet[ChannelName]]:
    """The channels each recording holds frames on, which is what its row offers a box for.

    A recording the picker never chose on a channel contributes nothing there whatever the
    reader ticks, so the row draws a box exactly where the choice reaches something. The frames
    the reader wrote gather under the authored stem, which offers its boxes the same way and
    appears exactly where it holds a frame.
    """
    offered: Dict[int, Set[ChannelName]] = {entry.id: set() for entry in stems_data.config.entries}
    for channel_name, stem_ids in stems_data.assignments_by_channel.items():
        for stem_id in set(stem_ids):
            if stem_id == AUTHORED_STEM_ID:
                offered.setdefault(AUTHORED_STEM_ID, set()).add(channel_name)
            elif stem_id in offered:
                offered[stem_id].add(channel_name)

    return {stem_id: frozenset(channels) for stem_id, channels in offered.items()}
