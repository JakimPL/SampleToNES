import operator
from pathlib import Path
from typing import Final, List

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.project import ProjectContainer
from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.screens.history.constants import LEAD
from tests.screens.history.steps import expect_lines, history_count, press_on_the_sequencer
from tests.suite.history.audit import fresh_fingerprint
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.project import save_project_as
from tests.suite.screens.steps.sequencer import open_voice

BEFORE: Final[Path] = PROJECTS_DIRECTORY / "Before.stp"
AFTER: Final[Path] = PROJECTS_DIRECTORY / "After.stp"
TEMPO: Final[int] = 99
TRACKER_ROW: Final[int] = 3
TRACKER_VOLUME: Final[str] = "2"
LEAD_VOLUME: Final[str] = "6 6"
TAKEN_OUT: Final[str] = "1"


class TestEveryEditUndoneLeavesTheSavedProject:
    """A project saved, edited on both tabs and undone back to the save reads clean and saves as it was saved.

    The project is saved as one file, then a tracker volume, the tempo, a sample's volume and a recording
    taken out each add a line. Four undos bring the title back to clean, a save to a second file follows, and
    both files describe the same project; the exit then asks nothing.
    """

    def test_the_second_file_is_the_first(self, screen: Screen) -> None:
        lines: List[int] = []

        def save_the_project_first(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            save_project_as(screen, BEFORE)
            lines.append(history_count(screen))

        def edit_on_both_tabs(screen: Screen) -> None:
            tracker = screen.sequencer.tracker
            tracker.click(TRACKER_ROW, ChannelName.PULSE2, SubColumn.VOLUME)
            screen.hand.type_text(TRACKER_VOLUME)
            expect_lines(screen, lines[0] + 1)

            screen.sequencer.module.retype_tempo(TEMPO)
            expect_lines(screen, lines[0] + 2)

            open_voice(screen, LEAD)
            screen.expect(screen.tabs.front, Tab.RECONSTRUCTIONS.__eq__, description="Lead open")
            screen.reconstructions.instruments.type_envelope(ChannelName.PULSE1, FeatureKey.VOLUME, LEAD_VOLUME)
            expect_lines(screen, lines[0] + 3)

            stems = screen.reconstructions.stems
            stems.remove(TAKEN_OUT)
            screen.expect(stems.remove_prompt.is_shown, bool, description="the question about removing")
            stems.remove_prompt.confirm()
            expect_lines(screen, lines[0] + 4)

        def undo_everything(screen: Screen) -> None:
            history = screen.sequencer.history
            for _ in range(4):
                press_on_the_sequencer(screen, ShortcutId.UNDO)

            screen.expect(lambda: history.lines()[-1].current, bool, description="the saved line in force")
            screen.expect(screen.project.unsaved_prompt.is_shown, operator.not_, description="no question open")

        def save_again_and_compare(screen: Screen) -> None:
            save_project_as(screen, AFTER)

            assert fresh_fingerprint(ProjectContainer.load(AFTER)) == fresh_fingerprint(ProjectContainer.load(BEFORE))

        def leave_asking_nothing(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)

            assert screen.wait_for_exit()

        screen.scenario(
            save_the_project_first,
            edit_on_both_tabs,
            undo_everything,
            save_again_and_compare,
            leave_asking_nothing,
        ).run()
