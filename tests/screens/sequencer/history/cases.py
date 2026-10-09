import operator
from functools import partial
from typing import Callable, Final, Tuple

from automation.screen import Screen
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.sequencer.history.steps import pick, rename

DUPLICATE: Final[str] = "sequencer.voices.label.context_duplicate"
Gesture = Callable[[Screen, str], None]


def duplicate(screen: Screen, name: str) -> None:
    """Duplicates the voice ``name`` from the context menu of its row."""
    voices = screen.sequencer.voices
    menu = screen.context_menu
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    voices.right_click(screen.expect_item(partial(voices.row, name), description=f"the row of {name}"))
    screen.expect(menu.is_shown, bool, description="the row's menu")
    menu.choose(screen.words(DUPLICATE))


def move(screen: Screen, name: str) -> None:
    """Moves the voice ``name`` one place, down where a place lies below it and up otherwise."""
    last = screen.sequencer.voices.names()[-1] == name
    pick(screen, name)
    screen.press_shortcut(ShortcutId.VOICES_MOVE_VOICE_UP if last else ShortcutId.VOICES_MOVE_VOICE_DOWN)


def remove(screen: Screen, name: str) -> None:
    """Removes the voice ``name`` by shortcut and confirms the question about removing."""
    prompt = screen.sequencer.voices.remove_prompt
    pick(screen, name)
    screen.press_shortcut(ShortcutId.VOICES_REMOVE_VOICE)
    screen.expect(prompt.is_shown, bool, description="the question about removing")
    prompt.confirm()
    screen.expect(prompt.is_shown, operator.not_, description="the question answered")


GESTURES: Final[Tuple[Tuple[str, Gesture], ...]] = (
    ("rename", rename),
    ("duplicate", duplicate),
    ("move", move),
    ("remove", remove),
)
