from typing import Dict, FrozenSet, Optional, Set

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

    Soloing a recording silences every other one and remembers the choice it replaced, so soloing
    it again returns to that choice. A choice made by hand afterwards stands as the new state.
    """

    def __init__(self) -> None:
        self._offered: Dict[int, FrozenSet[ChannelName]] = {}
        self._heard: Dict[int, FrozenSet[ChannelName]] = {}
        self._heard_before_solo: Optional[Dict[int, FrozenSet[ChannelName]]] = None

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
        self._heard_before_solo = None

    def set_channels(self, stem_id: int, channels: FrozenSet[ChannelName]) -> None:
        """Takes the channels one recording is heard on, as a box on its row leaves them."""
        self._heard[stem_id] = channels
        self._heard_before_solo = None

    def solo(self, stem_id: int) -> None:
        """Hears one recording on every channel it offers and silences the others.

        The choice in force when the first solo starts is remembered, so soloing the recording
        again returns to it, whichever recordings were soloed in between. Where nothing is
        remembered, every recording is heard whole. A recording offering no channel has nothing
        to hear alone.
        """
        if not self._offered.get(stem_id):
            return

        if self._is_alone(stem_id):
            restored = self._heard_before_solo if self._heard_before_solo is not None else dict(self._offered)
            self._heard_before_solo = None
            self._heard = restored
            return

        if not any(self._is_alone(other_id) for other_id in self._offered):
            self._heard_before_solo = dict(self._heard)

        self._heard = {
            offered_id: channels if offered_id == stem_id else frozenset()
            for offered_id, channels in self._offered.items()
        }

    def release(self) -> None:
        """Lets go of the choice, which is what closing the reconstruction it describes does."""
        self._offered = {}
        self._heard = {}
        self._heard_before_solo = None

    def _is_alone(self, stem_id: int) -> bool:
        """Whether the recording is heard on every channel it offers while no other is heard at all."""
        offered = self._offered.get(stem_id, frozenset())
        if not offered or self._heard.get(stem_id, frozenset()) != offered:
            return False

        return all(not channels for other_id, channels in self._heard.items() if other_id != stem_id)


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
