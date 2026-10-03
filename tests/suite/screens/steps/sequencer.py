from functools import partial
from typing import Final

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.screen import Screen

EDIT_VOICE: Final[str] = "sequencer.voices.label.context_edit"
HOVER_RACE: Final[str] = "Error executing callback _on_row_hovered"


def voice_row(screen: Screen, name: str) -> Item:
    """The Voices card's row of the voice ``name``, on the Sequencer tab brought to the front."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    voices = screen.sequencer.voices
    return screen.expect_item(partial(voices.row, name), description=f"the row of {name}")


def double_click_voice(screen: Screen, name: str) -> None:
    """Double-clicks the voice ``name``, which opens it on the Reconstructions tab."""
    screen.sequencer.voices.edit(voice_row(screen, name))


def open_voice_menu(screen: Screen, name: str) -> None:
    """Right-clicks the row of the voice ``name``, which opens its menu."""
    screen.sequencer.voices.right_click(voice_row(screen, name))
    screen.expect(screen.context_menu.is_shown, bool, description=f"the menu of {name}")


def open_voice(screen: Screen, name: str) -> None:
    """Opens the voice ``name`` on the Reconstructions tab through Edit on its row's menu."""
    open_voice_menu(screen, name)
    screen.context_menu.choose(screen.words(EDIT_VOICE))


def forgive_the_hover_race(screen: Screen) -> None:
    """Forgives the error a voice row's hover meets once the list has rebuilt the row, which the ledger
    records.
    """
    screen.forgive_known_error(HOVER_RACE)


def leave_letting_the_project_go(screen: Screen) -> None:
    """Exits, letting the changed project go at the question about it."""
    forgive_the_hover_race(screen)
    prompt = screen.project.unsaved_prompt
    screen.press_shortcut(ShortcutId.EXIT)
    screen.expect(prompt.is_shown, bool, description="the question about the project")

    prompt.confirm()

    assert screen.wait_for_exit()


def on_the_sequencer(screen: Screen) -> None:
    """Brings the Sequencer tab to the front and waits until the project's voices are listed."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    screen.expect(screen.sequencer.voices.names, bool, description="the project's voices")
