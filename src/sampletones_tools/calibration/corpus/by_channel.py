from typing import Final, List

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import render_channels

from .families import Catalog
from .item import CorpusItem, StemsSources
from .stems import side_by_side, single_line

BY_CHANNEL_SUFFIX: Final[str] = "-by-channel"


class UnwrittenSoundError(ValueError):
    """Raised when a sound to convert channel by channel was not written as NES frames."""


def by_channel(item: CorpusItem, config: Config) -> CorpusItem:
    """The written sound once more, converted channel by channel: each channel's frames a stem of its own.

    Each stem is held to the channel that plays it, so the conversion knows which channel carries
    which part and is left the matching alone. Set beside the sound converted as one recording, it
    tells a failure of taking the parts apart from a failure of matching each part. The sound and its
    truth stay those of the written sound, and the stems are its channels as they render.

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
    stems = StemsSources(
        sources=tuple(np.asarray(rendered[channel], dtype=np.float32) for channel in channels),
        config=side_by_side([single_line([channel]) for channel in channels]),
    )
    return CorpusItem(
        name=f"{item.name}{BY_CHANNEL_SUFFIX}",
        family=item.family,
        category=by_channel_category(item.category),
        listed=item.listed,
        audio=item.audio,
        truth=truth,
        channels=stems.channels,
        stems=stems,
    )


def with_by_channel(items: List[CorpusItem], config: Config) -> List[CorpusItem]:
    """The written sounds, then each of them once more converted channel by channel."""
    return [*items, *(by_channel(item, config) for item in items)]


def with_by_channel_catalog(catalog: Catalog) -> Catalog:
    """The categories of written sounds, then each again for the sounds converted channel by channel."""
    return [*catalog, *((family, by_channel_category(category)) for family, category in catalog)]


def by_channel_category(category: str) -> str:
    """The category a written sound of ``category`` falls in once converted channel by channel."""
    return f"{category}{BY_CHANNEL_SUFFIX}"
