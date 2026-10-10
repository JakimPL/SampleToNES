from dataclasses import dataclass
from typing import FrozenSet, List, Mapping, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones_core.audio.mixing import align, mix
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.filter import filter_approximations
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection


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
