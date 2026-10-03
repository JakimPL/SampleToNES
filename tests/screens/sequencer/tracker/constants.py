from typing import Final, Optional

from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.dearpygui.keys import IMGUI_LETTER_A

PIANO_C: Final[int] = IMGUI_LETTER_A + ord("z") - ord("a")
TYPING_FRAMES: Final[int] = 10
LINE_NUMBER: Final[str] = "00"
PAD_NUMBER: Final[str] = "02"
SAMPLE_COLUMN: Final[Optional[ChannelName]] = None
