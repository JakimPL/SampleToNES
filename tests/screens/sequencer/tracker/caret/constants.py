from typing import Final

from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName

CHANNEL: Final[ChannelName] = ChannelName.PULSE2
SLOT: Final[SubColumn] = SubColumn.VOICE
CLICKED_ROW: Final[int] = 2
QUIET_FRAMES: Final[int] = 3
LANDING_FRAMES: Final[int] = 6
BURST: Final[int] = 3
FIRST_POSITION: Final[int] = 0
FIRST_CHARACTER: Final[int] = 0
SECOND_CHARACTER: Final[int] = 1
TYPED_DIGIT: Final[str] = "0"
TYPING_FRAMES: Final[int] = 10
COLOR_TOLERANCE: Final[float] = 0.12
RGB: Final[int] = 3
