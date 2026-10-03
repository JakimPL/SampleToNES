import operator
from functools import partial
from typing import Final, Tuple

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.settings import (
    TAG_SETTINGS_AUDIO_WINDOW,
    TAG_SETTINGS_DISPLAY_WINDOW,
    TAG_SETTINGS_KEYBINDINGS_WINDOW,
    TAG_SETTINGS_PROPERTIES_WINDOW,
    TAG_SETTINGS_RENDER_WINDOW,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.interface.shortcuts.constants import SETTLING_FRAMES
from tests.screens.interface.shortcuts.steps import on_a_tab
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.dearpygui.items.reading import is_tag_within
from tests.suite.screens.dearpygui.items.regions import read_windows
from tests.suite.screens.dearpygui.keys import IMGUI_ESCAPE
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import expect_open
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION

DIALOG_SHORTCUTS: Final[Tuple[Tuple[ShortcutId, str], ...]] = (
    (ShortcutId.DISPLAY_SETTINGS, TAG_SETTINGS_DISPLAY_WINDOW),
    (ShortcutId.KEYBOARD_SETTINGS, TAG_SETTINGS_KEYBINDINGS_WINDOW),
    (ShortcutId.AUDIO_SETTINGS, TAG_SETTINGS_AUDIO_WINDOW),
    (ShortcutId.PROJECT_PROPERTIES, TAG_SETTINGS_PROPERTIES_WINDOW),
    (ShortcutId.RENDER_SONG, TAG_SETTINGS_RENDER_WINDOW),
)

FILE_SHORTCUTS: Final[Tuple[Tuple[ShortcutId, DialogKind], ...]] = (
    (ShortcutId.SAVE_PROJECT_AS, DialogKind.SAVE),
    (ShortcutId.EXPORT_PROJECT_FAMITRACKER, DialogKind.SAVE),
    (ShortcutId.EXPORT_PROJECT_BITPHASE, DialogKind.SAVE),
    (ShortcutId.RECONSTRUCT_FILE, DialogKind.OPEN),
    (ShortcutId.RECONSTRUCT_DIRECTORY, DialogKind.DIRECTORY),
    (ShortcutId.OPEN_RECONSTRUCTION, DialogKind.OPEN),
    (ShortcutId.SAVE_RECONSTRUCTION_AS, DialogKind.SAVE),
    (ShortcutId.EXPORT_RECONSTRUCTION_WAV, DialogKind.SAVE),
    (ShortcutId.EXPORT_INSTRUMENTS_FAMITRACKER, DialogKind.SAVE),
)


def window_standing(window: str) -> bool:
    """Whether a window standing under ``window`` is shown. Runs on the render thread."""
    return any(reading.shown and is_tag_within(reading.alias, window) for reading in read_windows())


class TestShortcutsOpeningDialogs:
    """Each shortcut printed for a dialog opens that dialog, and each one printed for a file asks for that
    file.

    Open project asks about the project already open first: Cancel takes the question back with no
    file requested, and a second try followed by Confirm requests the file.
    """

    def test_each_opens_what_it_names(self, screen: Screen) -> None:
        def each_dialog_shortcut(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            for shortcut_id, window in DIALOG_SHORTCUTS:
                on_a_tab(screen, Tab.RECONSTRUCTIONS)

                screen.press_shortcut(shortcut_id)

                screen.expect(lambda: screen.bridge.ask(partial(window_standing, window)), bool, description=window)
                screen.hand.press_key(IMGUI_ESCAPE, modifiers=[])
                screen.expect(
                    lambda: screen.bridge.ask(partial(window_standing, window)),
                    operator.not_,
                    description=f"{window} closed",
                )

        def each_file_shortcut(screen: Screen) -> None:
            for shortcut_id, kind in FILE_SHORTCUTS:
                on_a_tab(screen, Tab.RECONSTRUCTIONS)
                asked = len(screen.dialog_requests())
                screen.answer_next_dialog(kind, None)

                screen.press_shortcut(shortcut_id)

                screen.expect(
                    lambda: len(screen.dialog_requests()),
                    (asked + 1).__eq__,
                    description=f"the file {shortcut_id} asks for",
                )
                assert screen.dialog_requests()[-1].kind == kind

        def open_project_asks_about_the_open_one_first(screen: Screen) -> None:
            prompt = screen.project.replace_prompt
            on_a_tab(screen, Tab.SEQUENCER)
            asked = len(screen.dialog_requests())
            screen.press_shortcut(ShortcutId.OPEN_PROJECT)
            screen.expect(prompt.is_shown, bool, description="the question about the open project")

            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question taken back")
            screen.frames(SETTLING_FRAMES)
            assert len(screen.dialog_requests()) == asked
            screen.answer_next_dialog(DialogKind.OPEN, None)
            screen.press_shortcut(ShortcutId.OPEN_PROJECT)
            screen.expect(prompt.is_shown, bool, description="the question again")
            prompt.confirm()
            screen.expect(
                lambda: len(screen.dialog_requests()), (asked + 1).__eq__, description="the project asked for"
            )
            assert screen.dialog_requests()[-1].kind == DialogKind.OPEN

        screen.scenario(each_dialog_shortcut, each_file_shortcut, open_project_asks_about_the_open_one_first).run()
