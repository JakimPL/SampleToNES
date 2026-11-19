from typing import Final, List

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_core.generators import render_channels
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

from .item import CorpusItem, StemsSources

BY_CHANNEL_SUFFIX: Final[str] = "-by-channel"
UNIT_DRIVE: Final[float] = 1.0
ONE_CHANNEL: Final[int] = 1


class UnwrittenSoundError(ValueError):
    """Raised when a sound to convert channel by channel was not written as NES frames."""


def by_channel(item: CorpusItem, config: Config) -> CorpusItem:
    """The written sound once more, converted channel by channel: each channel's frames a stem of its own.

    Each stem is held to the channel that plays it, so the conversion knows which channel carries
    which part and is left the matching alone. Set beside the sound converted as one recording, it
    tells a failure of taking the parts apart from a failure of matching each part.

    Args:
        item: A sound written as NES frames.
        config: The configuration the frames are rendered at.

    Returns:
        CorpusItem: The same sound and truth, named and categorized with ``-by-channel``.

    Raises:
        UnwrittenSoundError: If the sound was not written as NES frames.
    """
    truth = item.truth
    if truth is None or not truth.instructions:
        raise UnwrittenSoundError(f"{item.name!r} was not written as NES frames")

    rendered = render_channels(truth.instructions, config)
    channels = [channel for channel in ChannelName.items() if channel in rendered]
    entries = tuple(
        StemEntry(
            id=index,
            settings=StemSettings(
                channels=(channel,),
                bends=(channel,) if channel in TONE_CHANNELS else (),
                drives={channel: UNIT_DRIVE},
                channel_cap=ONE_CHANNEL,
            ),
        )
        for index, channel in enumerate(channels)
    )
    stems = StemsConfig(entries=entries, hierarchy=StemsHierarchy(levels=(tuple(range(len(channels))),)))
    return CorpusItem(
        name=f"{item.name}{BY_CHANNEL_SUFFIX}",
        family=item.family,
        category=f"{item.category}{BY_CHANNEL_SUFFIX}",
        listed=item.listed,
        audio=item.audio,
        truth=truth,
        channels=frozenset(channels),
        stems=StemsSources(
            sources=tuple(np.asarray(rendered[channel], dtype=np.float32) for channel in channels),
            config=stems,
        ),
    )


def with_by_channel(items: List[CorpusItem], config: Config) -> List[CorpusItem]:
    """The written sounds, then each of them once more converted channel by channel."""
    return [*items, *(by_channel(item, config) for item in items)]
