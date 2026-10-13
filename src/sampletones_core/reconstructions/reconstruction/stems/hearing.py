from dataclasses import dataclass
from typing import AbstractSet, Dict, FrozenSet, List, Mapping, Optional, Set

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones_core.audio.mixing import align, mix
from sampletones_core.constants.algorithm import AUTHORED_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.filter import filter_approximations
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection

HeardChannels = Mapping[int, FrozenSet[ChannelName]]


class Hearing(BaseModel):
    """What a reader hears of a document: the recordings heard on each channel, and the channels kept on.

    The two choices compose. The recordings heard filter each channel's frames, and the channels
    kept on choose which of the filtered channels play and are drawn. Both are the reader's
    listening state, so one hearing names one reading of a document wherever the reading is taken.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    selection: StemSelection
    channels_on: FrozenSet[ChannelName]

    def filter_for(
        self,
        channel: ChannelName,
        stems_data: StemsData,
    ) -> Optional[FrozenSet[int]]:
        """The owners of ``channel`` the reader hears, where an owner is left out.

        A channel every owner of which is heard is heard whole, which ``None`` names, so two hearings
        leaving nothing out on a channel read it the same way whatever else they hear. Recordings
        heard that hold no frame on the channel change nothing there and are left out of the answer.

        Args:
            channel: The channel read.
            stems_data: The record naming the owner of each frame.

        Returns:
            Optional[FrozenSet[int]]: The owners heard, or ``None`` where every owner is heard.
        """
        owners = stems_data.owners_by_channel.get(channel, frozenset())
        heard = self.selection.stems_for(channel) & owners
        return None if heard == owners else heard


def offered_channels(stems_data: StemsData) -> Dict[int, FrozenSet[ChannelName]]:
    """The channels each recording holds frames on, which is what its row offers a box for.

    A recording the picker never chose on a channel contributes nothing there whatever the
    reader ticks, so the row draws a box exactly where the choice reaches something. A recording
    holding no frame anywhere has left the document, so every recording offers a box somewhere
    once any of them holds a frame. The frames the reader wrote gather under the authored stem,
    which offers its boxes the same way and appears exactly where it holds a frame.

    Args:
        stems_data: The record naming the owner of each frame.

    Returns:
        Dict[int, FrozenSet[ChannelName]]: The channels each recording of the record offers, and
        the authored row's where it holds a frame.
    """
    offered: Dict[int, Set[ChannelName]] = {entry.id: set() for entry in stems_data.config.entries}
    for channel_name, stem_ids in stems_data.assignments_by_channel.items():
        for stem_id in set(stem_ids):
            if stem_id == AUTHORED_STEM_ID:
                offered.setdefault(AUTHORED_STEM_ID, set()).add(channel_name)
            elif stem_id in offered:
                offered[stem_id].add(channel_name)

    return {stem_id: frozenset(channels) for stem_id, channels in offered.items()}


def selection_of(heard: HeardChannels) -> StemSelection:
    """What a reader hears, read the way the filters ask for it.

    A listening keeps the channels each recording is heard on; a filter asks each channel which
    recordings it keeps, so the selection is that map turned around, with every channel a key.

    Args:
        heard: The channels each recording is heard on.

    Returns:
        StemSelection: The recordings heard on each channel.
    """
    channels: Dict[ChannelName, Set[int]] = {channel_name: set() for channel_name in ChannelName.items()}
    for stem_id, stem_channels in heard.items():
        for channel_name in stem_channels:
            channels[channel_name].add(stem_id)

    return StemSelection(channels={channel_name: frozenset(stem_ids) for channel_name, stem_ids in channels.items()})


def heard_by_stem(
    selection: StemSelection,
    offered: HeardChannels,
) -> Dict[int, FrozenSet[ChannelName]]:
    """The channels each recording of ``offered`` is heard on under ``selection``, the selection turned back around.

    Args:
        selection: The recordings heard on each channel.
        offered: The channels each recording holds frames on.

    Returns:
        Dict[int, FrozenSet[ChannelName]]: One entry per recording offered, holding the channels
        it offers that hear it.
    """
    return {
        stem_id: frozenset(channel_name for channel_name in channels if stem_id in selection.stems_for(channel_name))
        for stem_id, channels in offered.items()
    }


def carried_heard(
    heard: HeardChannels,
    offered_before: HeardChannels,
    offered_after: HeardChannels,
) -> Dict[int, FrozenSet[ChannelName]]:
    """The channels each recording is heard on once a record stands in place of the one the choice was made on.

    A recording keeps whatever was chosen for it on a channel it keeps holding frames on, and is
    heard on every channel it reaches for the first time. Read against the nothing it offered
    before, that hears a recording appearing for the first time on all it holds, so a freshly
    opened document is heard whole and the frames a reader first writes on a channel join what is
    heard there. A recording the new record leaves out leaves the choice with it.

    Args:
        heard: The channels each recording is heard on, as the reader left them.
        offered_before: The channels each recording offered on the record the choice was made on.
        offered_after: The channels each recording offers on the record now standing.

    Returns:
        Dict[int, FrozenSet[ChannelName]]: One entry per recording offered now.
    """
    return {
        stem_id: (heard.get(stem_id, frozenset()) & channels) | (channels - offered_before.get(stem_id, frozenset()))
        for stem_id, channels in offered_after.items()
    }


def carried_channels_on(
    channels_on: AbstractSet[ChannelName],
    playing_before: AbstractSet[ChannelName],
    playing_after: AbstractSet[ChannelName],
) -> FrozenSet[ChannelName]:
    """The channels kept on once the document plays ``playing_after``.

    A channel coming into play joins the channels on, one kept playing keeps the reader's choice
    for it, and one leaving play leaves them.

    Args:
        channels_on: The playing channels the reader kept on.
        playing_before: The channels the document played when the choice was made.
        playing_after: The channels the document plays now.

    Returns:
        FrozenSet[ChannelName]: The channels on, every one of them playing.
    """
    return frozenset((channels_on & playing_after) | (playing_after - playing_before))


def carried_hearing(
    hearing: Hearing,
    *,
    offered_before: HeardChannels,
    playing_before: AbstractSet[ChannelName],
    offered_after: HeardChannels,
    playing_after: AbstractSet[ChannelName],
) -> Hearing:
    """``hearing`` carried onto a record offering ``offered_after`` and a document playing ``playing_after``.

    One rule carries the reader's choice across an edit wherever a new record is met: the
    regeneration worker applies it to the document it rebuilt, and the listening state to the
    document that lands, so the two agree on what is heard and the sound and envelopes a landing
    installs are the ones the listening then reads.

    Args:
        hearing: What the reader heard of the document the choice was made on.
        offered_before: The channels each recording offered on that document.
        playing_before: The channels that document played.
        offered_after: The channels each recording offers on the document now standing.
        playing_after: The channels that document plays.

    Returns:
        Hearing: What the reader hears of the document now standing.
    """
    heard = heard_by_stem(hearing.selection, offered_before)
    return Hearing(
        selection=selection_of(carried_heard(heard, offered_before, offered_after)),
        channels_on=carried_channels_on(hearing.channels_on, playing_before, playing_after),
    )


def hearing_carried_onto(
    hearing: Hearing,
    before: Reconstruction,
    after: Reconstruction,
) -> Hearing:
    """``hearing``, made on ``before``, carried onto ``after``.

    A rebuild's worker hears the document it leaves this way, so the reading it renders and the
    envelopes it exports are the ones the listening asks for once the document lands.

    Args:
        hearing: What the reader heard of ``before``.
        before: The document the choice was made on.
        after: The document now standing, such as the one a rebuild leaves.

    Returns:
        Hearing: What the reader hears of ``after``.
    """
    return carried_hearing(
        hearing,
        offered_before=offered_channels(before.stems_data),
        playing_before=frozenset(before.playing_channels),
        offered_after=offered_channels(after.stems_data),
        playing_after=frozenset(after.playing_channels),
    )


def whole_hearing(reconstruction: Reconstruction) -> Hearing:
    """Every recording and the reader's own row heard wherever they hold frames, every playing channel on.

    It is the carry from a record offering nothing and a document playing nothing, which is how a
    freshly opened document is heard, so a reading taken for it keys the render cache the way the
    listening state keys the same document.

    Args:
        reconstruction: The document heard.

    Returns:
        Hearing: The document heard whole.
    """
    return carried_hearing(
        Hearing(selection=StemSelection(channels={}), channels_on=frozenset()),
        offered_before={},
        playing_before=frozenset(),
        offered_after=offered_channels(reconstruction.stems_data),
        playing_after=frozenset(reconstruction.playing_channels),
    )


@dataclass(frozen=True)
class HeardRenders:
    """The audio a hearing of a document sounds.

    Attributes:
        mix: Every channel in play mixed, the frames of the recordings left out silenced.
        playing: The channels kept on mixed the same way, which is what plays and is drawn.
    """

    mix: np.ndarray
    playing: np.ndarray


def heard_renders(
    reconstruction: Reconstruction,
    hearing: Hearing,
    channels: Mapping[ChannelName, np.ndarray],
    mixed: np.ndarray,
) -> HeardRenders:
    """What ``hearing`` sounds of ``reconstruction``, read from its channels' renders and their mix.

    A hearing leaving no recording out sounds ``mixed`` itself, and one keeping every channel on
    plays what it mixes, so a reading that filters nothing hands the arrays it was given back by
    identity. A narrower choice of channels is summed in channel order, so the same choice reads the
    same samples whatever order it was made in.

    Args:
        reconstruction: The document read.
        hearing: What the reader hears of it.
        channels: The render of every channel in play, by channel.
        mixed: The mix of ``channels``.

    Returns:
        HeardRenders: The heard mix and what plays.
    """
    approximations = filter_approximations(
        reconstruction.stems_data,
        channels,
        hearing.selection,
        reconstruction.config.frame_length,
    )
    heard_whole = all(filtered is channels[name] for name, filtered in approximations.items())
    heard_mix = mixed if heard_whole else mix(list(approximations.values()))
    playing: List[np.ndarray] = [
        approximations[name] for name in ChannelName.items() if name in hearing.channels_on and name in approximations
    ]
    if len(playing) == len(approximations):
        return HeardRenders(mix=heard_mix, playing=heard_mix)

    if not playing:
        return HeardRenders(mix=heard_mix, playing=np.zeros_like(heard_mix))

    return HeardRenders(mix=heard_mix, playing=mix(align(playing, len(heard_mix))))
