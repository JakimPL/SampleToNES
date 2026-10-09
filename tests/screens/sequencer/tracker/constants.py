from typing import Final, Optional

from automation.dearpygui.keys import IMGUI_LETTER_A
from sampletones_core.constants.enums import ChannelName

PIANO_C: Final[int] = IMGUI_LETTER_A + ord("z") - ord("a")
TYPING_FRAMES: Final[int] = 10
LINE_NUMBER: Final[str] = "00"
PAD_NUMBER: Final[str] = "02"
SAMPLE_COLUMN: Final[Optional[ChannelName]] = None
PLAY_FROM_THIS_FRAME: Final[str] = "sequencer.tracker.label.context_play_from_frame"
