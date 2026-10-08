from typing import List

import pytest

from automation.application.startup import Startup
from automation.holds.conversion import ConversionHold
from automation.holds.regeneration import RegenerationHold
from automation.screen import Screen
from automation.steps.main import gather, home_path
from automation.steps.project import retitle_project
from automation.steps.reconstructions import expect_open, raise_the_first_level_while_held
from automation.worlds.home import World
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.screens.application.closing.constants import NEW_TITLE, RUN_TIMEOUT_SECONDS
from tests.screens.application.closing.steps import asks_about_the_conversion, conversion_question
from tests.suite.screens.worlds.recordings import BASS, OPEN_RECONSTRUCTION, SONG, documents_world


class TestExitWithEverythingPending:
    """Exit with an unsaved project, an unsaved reconstruction and a conversion running asks about each, in
    that order, and leaves once the last is answered.

    The scenario retitles the project, edits the reconstruction, and starts a held conversion. Exit then
    asks about the project, the reconstruction and the conversion in turn; each is confirmed, and the
    application stops.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds the documents world: a project, a reconstruction and recordings."""
        return documents_world()

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the reconstruction and the project at start."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=SONG)

    def test_the_questions_come_in_order(
        self,
        screen: Screen,
        conversion_hold: ConversionHold,
        regeneration_hold: RegenerationHold,
    ) -> None:
        """The three questions appear as project, reconstruction, conversion."""
        converter = screen.main.converter
        asked: List[str] = []

        def change_both_documents_and_start_a_run(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            retitle_project(screen, NEW_TITLE)
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
            raise_the_first_level_while_held(screen, regeneration_hold, ChannelName.PULSE1)
            regeneration_hold.release()
            screen.tabs.bring_to_front(Tab.MAIN)
            gather(screen, home_path(BASS))
            converter.press_action()
            screen.bridge.expect(
                converter.progress,
                lambda progress: progress > 0,
                description="the run under way",
                timeout=RUN_TIMEOUT_SECONDS,
            )

        def answer_each_question(screen: Screen) -> None:
            project = screen.project.unsaved_prompt
            reconstruction = screen.reconstructions.unsaved_prompt
            screen.press_shortcut(ShortcutId.EXIT)

            screen.expect(project.is_shown, bool, description="the question about the project")
            asked.append("project")
            project.confirm()
            screen.expect(
                lambda: reconstruction.is_shown() and not asks_about_the_conversion(screen),
                bool,
                description="the question about the reconstruction",
            )
            asked.append("reconstruction")
            reconstruction.confirm()
            screen.expect(lambda: asks_about_the_conversion(screen), bool, description="the question about the run")
            asked.append("conversion")
            conversion_question(screen).confirm()

            assert screen.wait_for_exit()
            assert asked == ["project", "reconstruction", "conversion"]

        screen.scenario(change_both_documents_and_start_a_run, answer_each_question).run()
