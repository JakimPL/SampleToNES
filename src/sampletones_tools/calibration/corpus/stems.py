from typing import Final, List, Sequence

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

SINGLE_LINE_CAP: Final[int] = 1


def single_line(channels: List[ChannelName]) -> StemSettings:
    """A stem playing one line: the usual settings over ``channels``, sounding one of them at a time.

    A melody, a bass line, a drum part or one channel's frames is a single line, so its stem holds
    the conversion to one channel per frame among those it may take.
    """
    return StemSettings.covering(channels).with_channel_cap(SINGLE_LINE_CAP)


def side_by_side(settings: Sequence[StemSettings]) -> StemsConfig:
    """A setup of stems converted side by side, one entry per stem in order.

    Every entry stands on one level of the hierarchy, so each stem is picked in the same round as the
    others, and the setup holds the parts of a sound as equals.
    """
    entries = tuple(StemEntry(id=index, settings=stem) for index, stem in enumerate(settings))
    return StemsConfig(entries=entries, hierarchy=StemsHierarchy(levels=(tuple(range(len(entries))),)))


def mixed(recordings: Sequence[np.ndarray]) -> np.ndarray:
    """The sound recordings of one length make together, which is their sum, in the corpus's float32."""
    return np.asarray(np.sum(recordings, axis=0)).astype(np.float32)
