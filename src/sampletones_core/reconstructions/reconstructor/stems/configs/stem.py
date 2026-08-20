from dataclasses import dataclass
from typing import FrozenSet

from sampletones_core.constants.enums import ChannelName


@dataclass(frozen=True)
class Stem:
    """
    One audio source competing for channels in a reconstruction, identified by its
    id and restricted to the channels it may occupy.
    """

    id: int
    channels: FrozenSet[ChannelName]
