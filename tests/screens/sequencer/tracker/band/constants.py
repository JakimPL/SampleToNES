from typing import Final, Tuple

from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import display_id
from sampletones_shared.constants.project import DEFAULT_ROWS_PER_PATTERN

FIRST_FRAME: Final[int] = 0
SECOND_FRAME: Final[int] = 1
LAST_ROW: Final[int] = DEFAULT_ROWS_PER_PATTERN - 1
CLICKED_ROW: Final[int] = 2
STEPS_DOWN: Final[int] = 3
NEIGHBORS: Final[int] = 3
CHANNEL: Final[ChannelName] = ChannelName.PULSE1
SLOT: Final[SubColumn] = SubColumn.VOICE
PLAYING_FRAMES: Final[int] = 90
BLANK: Final[str] = ""
LAST_ROWS_OF_A_FRAME: Final[Tuple[str, ...]] = tuple(
    display_id(row) for row in range(DEFAULT_ROWS_PER_PATTERN - NEIGHBORS, DEFAULT_ROWS_PER_PATTERN)
)
FIRST_ROWS_OF_A_FRAME: Final[Tuple[str, ...]] = tuple(display_id(row) for row in range(NEIGHBORS))
