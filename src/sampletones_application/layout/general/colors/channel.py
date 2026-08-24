from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor
from sampletones_core.constants.enums import ChannelName


class ChannelColors(BaseModel, extra="forbid", frozen=True):
    """The per-channel palette shared by every view that names a channel.

    The order table paints each channel's row label in its color, the tracker grid tints each
    channel's column background with the same color at a low alpha, and the waveform plots draw a
    generator's line in it, so a channel keeps one identity across the application.
    """

    pulse1: WrittenColor
    pulse2: WrittenColor
    triangle: WrittenColor
    noise: WrittenColor

    def for_channel(self, channel_name: ChannelName) -> WrittenColor:
        """The color this channel is known by."""
        match channel_name:
            case ChannelName.PULSE1:
                return self.pulse1
            case ChannelName.PULSE2:
                return self.pulse2
            case ChannelName.TRIANGLE:
                return self.triangle
            case ChannelName.NOISE:
                return self.noise
