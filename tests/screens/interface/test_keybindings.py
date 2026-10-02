import operator
from functools import partial
from typing import Dict, Final

import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.sequencer import TAG_SEQUENCER_VOICES_INPUT_RENAME
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.screens.application import Startup
from tests.suite.screens.dearpygui.items import read_item
from tests.suite.screens.dearpygui.keys import IMGUI_ENTER, IMGUI_ESCAPE
from tests.suite.screens.keyboard import press_combination
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import forgive_the_hover_race
from tests.suite.screens.world import ARRANGED_PROJECT, BASS_VOICE, LINE, PAD
from tests.suite.screens.written import written_application_config

LISTENING: Final[str] = "settings.keybindings.message.capturing"
NEW_UNDO: Final[KeyCombination] = KeyCombination.parse("Ctrl+Alt+U")
RENAMED: Final[str] = "Renamed"
SETTLING_FRAMES: Final[int] = 20


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


def rename_the_line(screen: Screen) -> None:
    """Renames the line through F2 on its row, which the history records."""
    voices = screen.sequencer.voices
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    voices.pick(screen.expect_item(partial(voices.row, LINE), description="the line's row"))
    screen.press_shortcut(ShortcutId.VOICES_RENAME_VOICE)
    screen.expect(
        lambda: screen.bridge.ask(lambda: read_item(TAG_SEQUENCER_VOICES_INPUT_RENAME)).shown,
        bool,
        description="the name being edited",
    )
    screen.hand.replace_text(TAG_SEQUENCER_VOICES_INPUT_RENAME, RENAMED)
    screen.hand.press_key(IMGUI_ENTER, modifiers=[])
    screen.expect(voices.names, [RENAMED, BASS_VOICE, PAD].__eq__, description="the line renamed")


class TestRebindingUndo:
    """Undo rebound: Escape cancels a capture, the new keys undo while the old ones do nothing, the menu prints the
    new keys, keys another action holds ask before they are taken, and leaving writes the rebind.
    """

    def test_the_new_keys_undo(self, screen: Screen) -> None:
        settings = screen.keyboard_settings
        voices = screen.sequencer.voices
        original: Dict[ShortcutId, str] = {}

        def escape_cancels_a_capture(screen: Screen) -> None:
            settings.open()
            screen.expect(settings.is_shown, bool, description="Keyboard settings")
            original.update(
                {shortcut_id: settings.keys_of(shortcut_id) for shortcut_id in (ShortcutId.UNDO, ShortcutId.REDO)}
            )
            settings.listen_for(ShortcutId.UNDO)
            screen.expect(
                partial(settings.keys_of, ShortcutId.UNDO), screen.words(LISTENING).__eq__, description="listening"
            )

            screen.hand.press_key(IMGUI_ESCAPE, modifiers=[])

            screen.expect(
                partial(settings.keys_of, ShortcutId.UNDO),
                original[ShortcutId.UNDO].__eq__,
                description="the keys back",
            )
            assert settings.is_shown()

        def rebind_undo(screen: Screen) -> None:
            settings.listen_for(ShortcutId.UNDO)

            press_combination(screen.hand, NEW_UNDO)

            screen.expect(
                partial(settings.keys_of, ShortcutId.UNDO),
                NEW_UNDO.display().__eq__,
                description="the new keys",
            )
            settings.confirm()
            screen.expect(settings.is_shown, operator.not_, description="Keyboard settings closed")
            undo = next(
                entry
                for entry in screen.menu.entries(MenuElements.GROUP_EDIT)
                if entry.label == screen.menu.label(MenuElements.ITEM_EDIT_UNDO)
            )
            assert undo.keys == NEW_UNDO.display()

        def the_old_keys_do_nothing_and_the_new_undo(screen: Screen) -> None:
            rename_the_line(screen)

            press_combination(screen.hand, KeyCombination.parse(original[ShortcutId.UNDO]))

            screen.frames(SETTLING_FRAMES)
            assert voices.names() == [RENAMED, BASS_VOICE, PAD]
            press_combination(screen.hand, NEW_UNDO)
            screen.expect(voices.names, [LINE, BASS_VOICE, PAD].__eq__, description="the rename undone")

        def keys_another_action_holds_ask_first(screen: Screen) -> None:
            reassign = settings.reassign_prompt
            settings.open()
            screen.expect(settings.is_shown, bool, description="Keyboard settings")
            settings.listen_for(ShortcutId.UNDO)

            press_combination(screen.hand, KeyCombination.parse(original[ShortcutId.REDO]))

            screen.expect(reassign.is_shown, bool, description="the question about reassigning")
            reassign.cancel()
            screen.expect(settings.is_shown, bool, description="Keyboard settings back")
            assert settings.keys_of(ShortcutId.REDO) == original[ShortcutId.REDO]
            settings.cancel()
            screen.expect(settings.is_shown, operator.not_, description="Keyboard settings closed")

        def leaving_writes_the_rebind(screen: Screen) -> None:
            forgive_the_hover_race(screen)
            screen.press_shortcut(ShortcutId.EXIT)

            assert screen.wait_for_exit()
            assert written_application_config().shortcuts.overrides == {ShortcutId.UNDO.value: NEW_UNDO.display()}

        screen.scenario(
            escape_cancels_a_capture,
            rebind_undo,
            the_old_keys_do_nothing_and_the_new_undo,
            keys_another_action_holds_ask_first,
            leaving_writes_the_rebind,
        ).run()
