from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import sounds

from .feature import Features
from .maps import CHANNEL_TO_EXPORTER_MAP


def stands_by(channel_name: ChannelName, features: Features) -> bool:
    """Whether a channel given these envelopes rests through every frame, and so stands by.

    An edit reaches a reconstruction as envelopes, which the regeneration rebuilds into the frames
    the channel plays. Reading them through that same rebuild answers what the document will hold
    before it holds it, so a figure measured as an edit arrives agrees with the one the
    regenerated document reports.

    Args:
        channel_name: The channel the envelopes are written into.
        features: The envelopes the channel is given.

    Returns:
        bool: True where no frame the envelopes describe sounds.
    """
    return not sounds(CHANNEL_TO_EXPORTER_MAP[channel_name].from_features(features))
