from typing import Dict, FrozenSet, Optional

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.hearing import (
    Hearing,
    carried_channels_on,
    carried_heard,
    offered_channels,
    selection_of,
)
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection


class Listening:
    """What a reader is listening to of the open reconstruction: the recordings heard on each channel, and
    the channels kept on.

    One choice serves every reading of the document: the frames it admits are the frames the
    waveform draws, the envelopes the instruments panel shows, the figures measuring them, what
    playback sounds and what an export writes, and they are the frames an edit reaches. Holding
    it beside the open reconstruction is what lets those readings answer from one state. The
    channels kept on are the boxes above the waveform: a channel switched off keeps every choice
    made for its recordings, so switching it back on restores them intact.

    The choice is the reader's, so it travels across an edit by the core's one rule
    (``carried_hearing``): a channel a recording keeps holding frames on keeps whatever was chosen
    for it, one the recording reaches for the first time joins heard, and a channel coming into
    play joins the channels on while one kept playing keeps the reader's choice for it. The
    regeneration worker carries the choice onto the document it rebuilds by the same rule, so the
    sound and the envelopes a landing installs are read for the choice this state then makes.

    Soloing a recording silences every other one and remembers the choice it replaced, so soloing
    it again returns to that choice. A choice made by hand afterwards stands as the new state.
    """

    def __init__(self) -> None:
        self._offered: Dict[int, FrozenSet[ChannelName]] = {}
        self._heard: Dict[int, FrozenSet[ChannelName]] = {}
        self._heard_before_solo: Optional[Dict[int, FrozenSet[ChannelName]]] = None
        self._playing: FrozenSet[ChannelName] = frozenset()
        self._channels_on: FrozenSet[ChannelName] = frozenset()

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
        """What the reader hears, read the way the filters ask for it: the heard map turned around."""
        return selection_of(self._heard)

    def heard_on(self, channel_name: ChannelName) -> FrozenSet[int]:
        """The recordings heard on one channel, which is the scope an edit writes in."""
        return self.selection.stems_for(channel_name)

    @property
    def playing(self) -> FrozenSet[ChannelName]:
        """The channels the document plays, which are the boxes above the waveform a reader can tick."""
        return self._playing

    @property
    def channels_on(self) -> FrozenSet[ChannelName]:
        """The playing channels the reader keeps on, which are what plays and what the waveform draws."""
        return self._channels_on

    @property
    def hearing(self) -> Hearing:
        """What the reader hears, as one value a reading of the document is taken for."""
        return Hearing(selection=self.selection, channels_on=self._channels_on)

    def adopt(self, stems_data: StemsData, playing: FrozenSet[ChannelName]) -> None:
        """Carries the reader's choice onto the record as it now stands, by the core's rule.

        A recording appearing for the first time offers everything it holds and is heard on all
        of it, which is the same rule read against the nothing it offered before, so a freshly
        opened reconstruction is heard whole. A channel coming into play joins the channels on
        the same way, and one kept playing keeps whatever the reader chose for it.

        Args:
            stems_data: The record naming the owner of each frame.
            playing: The channels the document plays.
        """
        offered = offered_channels(stems_data)
        self._heard = carried_heard(self._heard, self._offered, offered)
        self._offered = offered
        self._heard_before_solo = None
        self._channels_on = carried_channels_on(self._channels_on, self._playing, playing)
        self._playing = playing

    def set_channels_on(self, channels: FrozenSet[ChannelName]) -> None:
        """Takes the channels the reader keeps on, as the boxes above the waveform leave them."""
        self._channels_on = channels & self._playing

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
        """Lets go of the choice, which is what closing the reconstruction it describes, or opening another, does."""
        self._offered = {}
        self._heard = {}
        self._heard_before_solo = None
        self._playing = frozenset()
        self._channels_on = frozenset()

    def _is_alone(self, stem_id: int) -> bool:
        """Whether the recording is heard on every channel it offers while no other is heard at all."""
        offered = self._offered.get(stem_id, frozenset())
        if not offered or self._heard.get(stem_id, frozenset()) != offered:
            return False

        return all(not channels for other_id, channels in self._heard.items() if other_id != stem_id)
