from typing import Optional

from automation.screen import Screen
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.screens.sequencer.tracker.constants import TYPING_FRAMES


def play_a_note(screen: Screen, row: int, channel: ChannelName, key: int) -> None:
    """Clicks the transpose slot of a channel at a row, presses a piano key and lets the typing settle."""
    screen.sequencer.tracker.click(row, channel, SubColumn.TRANSPOSE)
    screen.hand.press_key(key, modifiers=[])
    screen.frames(TYPING_FRAMES)


def type_into(screen: Screen, row: int, channel: Optional[ChannelName], subcolumn: SubColumn, text: str) -> None:
    """Clicks a slot of a channel (or of the Sample column, when the channel is None), types the text
    and lets the typing settle.
    """
    screen.sequencer.tracker.click(row, channel, subcolumn)
    screen.hand.type_text(text)
    screen.frames(TYPING_FRAMES)
