from functools import partial

from automation.dearpygui.items.reading import read_item
from automation.dearpygui.keys import IMGUI_ENTER
from automation.screen import Screen
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.sequencer import TAG_SEQUENCER_VOICES_INPUT_RENAME
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.sequencer.history.constants import RENAMED, SETTLING_FRAMES


def pick(screen: Screen, name: str) -> None:
    """Opens the Sequencer tab, picks the row of the voice ``name`` and lets the screen settle."""
    voices = screen.sequencer.voices
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    row = screen.expect_item(partial(voices.row, name), description=f"the row of {name}")
    voices.pick(row)
    screen.frames(SETTLING_FRAMES)


def rename(screen: Screen, name: str) -> None:
    """Renames the voice ``name`` to the fixed new name: picks it, edits it and confirms."""
    pick(screen, name)
    screen.press_shortcut(ShortcutId.VOICES_RENAME_VOICE)
    screen.expect(
        lambda: screen.bridge.ask(lambda: read_item(TAG_SEQUENCER_VOICES_INPUT_RENAME)).shown,
        bool,
        description="the name being edited",
    )

    screen.hand.replace_text(TAG_SEQUENCER_VOICES_INPUT_RENAME, RENAMED)
    screen.hand.press_key(IMGUI_ENTER, modifiers=[])
