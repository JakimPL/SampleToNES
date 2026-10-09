import operator

from automation.screen import Screen
from automation.steps.reconstructions import UNTITLED, expect_open, titled
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.interface.shortcuts.steps import on_a_tab
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION


class TestShortcutsActingOnDocuments:
    """Each shortcut closing or starting a document does what its entry says.

    The scenario closes the reconstruction, closes the project, starts a new project, and leaves the
    application.
    """

    def test_each_acts_as_named(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        reconstructions = screen.reconstructions

        def documents_close_and_a_new_project_opens(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            on_a_tab(screen, Tab.SEQUENCER)
            screen.press_shortcut(ShortcutId.CLOSE_RECONSTRUCTION)
            screen.expect(reconstructions.file_line, operator.not_, description="the reconstruction closed")

            screen.press_shortcut(ShortcutId.CLOSE_PROJECT)
            screen.expect(voices.names, operator.not_, description="the project closed")

            screen.press_shortcut(ShortcutId.NEW_PROJECT)

            screen.expect(screen.title, titled(screen, screen.words(UNTITLED)).__eq__, description="a new project")

        def exit_leaves(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)

            assert screen.wait_for_exit()

        screen.scenario(documents_close_and_a_new_project_opens, exit_leaves).run()
