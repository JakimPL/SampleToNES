import operator
from typing import Dict, Final

import pytest

from automation.application.startup import Startup
from automation.holds.export import FIRST_REPORT, ExportHold
from automation.screen import Screen
from automation.steps.reconstructions import expect_open
from automation.views.notices import Notice
from sampletones_core.exports.stage import ExportStage
from tests.screens.exports.progress.cases import INSTRUMENT_DOORS, PROJECT_DOORS, ExportDoor
from tests.screens.exports.progress.steps import folder
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT

STAGE_WORDS: Final[Dict[ExportStage, str]] = {
    ExportStage.WALKING: "settings.export.label.stage_walking",
    ExportStage.COMPRESSING: "settings.export.label.stage_compressing",
    ExportStage.WRITING: "settings.export.label.stage_writing",
}

SETTLING_FRAMES: Final[int] = 20


def outcome_notice(screen: Screen, door: ExportDoor) -> Notice:
    """The notice a door's export ends with: the project notice for a project, the file notice otherwise."""
    return screen.exports.project_notice if door.project else screen.exports.file_notice


def canceled_and_then_written(screen: Screen, hold: ExportHold, door: ExportDoor) -> None:
    """Starts ``door``'s export under the hold, cancels it, and starts it again unheld, which writes.

    After the cancel the window is gone, the folder is empty and no notice appears.
    """
    progress = screen.exports.progress
    notice = outcome_notice(screen, door)
    into = folder(door.name)
    hold.hold_at(FIRST_REPORT)

    door.start(screen, into)

    screen.expect(progress.is_shown, bool, description=f"the {door.name} export under way")
    screen.expect(hold.waiting, (1).__eq__, description=f"the {door.name} export held")
    assert progress.stages() == (screen.words(STAGE_WORDS[door.first_stage]),)

    door.cancel(screen)

    screen.expect(progress.is_shown, operator.not_, description=f"the {door.name} export canceled")
    screen.frames(SETTLING_FRAMES)
    assert hold.waiting() == 0
    assert not notice.is_shown()
    assert list(into.iterdir()) == []

    hold.release()
    door.start(screen, into)

    screen.expect(notice.is_shown, bool, description=f"the {door.name} export written")
    assert not progress.is_shown()
    assert list(into.iterdir()) != []
    notice.dismiss()
    screen.expect(notice.is_shown, operator.not_, description="the notice gone")


class TestEveryExportAnswersCancel:
    """Every export shows its window while it runs, and a cancel stops it with the folder left empty; run to the end, it writes.

    The user cancels by clicking Cancel on some doors and pressing Escape on others.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=ARRANGED_PROJECT)

    def test_the_project_exports(self, screen: Screen, export_hold: ExportHold) -> None:
        def each_project_export(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            for door in PROJECT_DOORS:
                canceled_and_then_written(screen, export_hold, door)

        screen.scenario(each_project_export).run()

    def test_the_instrument_exports(self, screen: Screen, export_hold: ExportHold) -> None:
        def each_instrument_export(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            for door in INSTRUMENT_DOORS:
                canceled_and_then_written(screen, export_hold, door)

        screen.scenario(each_instrument_export).run()
