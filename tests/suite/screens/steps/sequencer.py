from functools import partial
from typing import Final

from sampletones_application.categories.hierarchy import Tab
from tests.suite.screens.dearpygui.items import Item
from tests.suite.screens.screen import Screen

EDIT_VOICE: Final[str] = "sequencer.voices.label.context_edit"


def voice_row(screen: Screen, name: str) -> Item:
    """The Voices card's row of the voice ``name``, on the Sequencer tab brought to the front."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    voices = screen.sequencer.voices
    return screen.expect_item(partial(voices.row, name), description=f"the row of {name}")


def double_click_voice(screen: Screen, name: str) -> None:
    """Double-clicks the voice ``name``, which opens it on the Reconstructions tab."""
    screen.sequencer.voices.edit(voice_row(screen, name))


def open_voice(screen: Screen, name: str) -> None:
    """Opens the voice ``name`` on the Reconstructions tab through Edit on its row's menu."""
    row = voice_row(screen, name)
    screen.sequencer.voices.right_click(row)
    screen.expect(screen.context_menu.is_shown, bool, description=f"the menu of {name}")
    screen.context_menu.choose(screen.words(EDIT_VOICE))
