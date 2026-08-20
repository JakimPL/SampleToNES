from typing import Dict, Final

from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_CHANNEL_NOISE,
    TAG_GLOBAL_THEME_CHANNEL_PULSE1,
    TAG_GLOBAL_THEME_CHANNEL_PULSE2,
    TAG_GLOBAL_THEME_CHANNEL_TRIANGLE,
)
from sampletones_core.constants.enums import ChannelName

CHANNEL_THEME_TAGS: Final[Dict[ChannelName, str]] = {
    ChannelName.PULSE1: TAG_GLOBAL_THEME_CHANNEL_PULSE1,
    ChannelName.PULSE2: TAG_GLOBAL_THEME_CHANNEL_PULSE2,
    ChannelName.TRIANGLE: TAG_GLOBAL_THEME_CHANNEL_TRIANGLE,
    ChannelName.NOISE: TAG_GLOBAL_THEME_CHANNEL_NOISE,
}
