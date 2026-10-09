from typing import Final, Optional, Tuple

from sampletones_core.constants.enums import ChannelName

CHANNEL_AXIS: Final[Tuple[Optional[ChannelName], ...]] = (None,) + tuple(ChannelName.items())
