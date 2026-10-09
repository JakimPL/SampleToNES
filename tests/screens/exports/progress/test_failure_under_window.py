import operator
from typing import Final

import pytest

from automation.application.startup import Startup
from automation.boundaries.dialogs import DialogKind
from automation.holds.export import ExportHold
from automation.screen import Screen
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_shared.paths.extensions import EXT_FILE_MODULE
from tests.screens.exports.progress.constants import FAILED_EXPORT, MODULE_EXPORTED
from tests.screens.exports.progress.steps import folder, written_project
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT

MODULE_FAILED: Final[str] = "global.dialog.message.project_export_failed"
READ_ONLY: Final[int] = 0o555
WRITABLE: Final[int] = 0o755


class TestAnExportFailingUnderItsWindow:
    """An export failing while its window stands closes the window and shows one error saying what failed, with the
    folder left empty; once the folder takes files again, the same export writes.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=ARRANGED_PROJECT)

    def test_the_error_follows_the_window(self, screen: Screen, export_hold: ExportHold) -> None:
        progress = screen.exports.progress
        into = folder("locked")
        destination = into / f"{ARRANGED_PROJECT.stem}{EXT_FILE_MODULE}"

        def start_the_module_export(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_FAMITRACKER)

            screen.expect(progress.is_shown, bool, description="the export under way")
            screen.expect(export_hold.waiting, (1).__eq__, description="the export held")

        def the_folder_refuses_the_file(screen: Screen) -> None:
            into.chmod(READ_ONLY)
            try:
                export_hold.release()

                screen.expect(screen.error_notice.is_shown, bool, description="the export failed")
            finally:
                into.chmod(WRITABLE)

            screen.claim_error(FAILED_EXPORT)
            assert not progress.is_shown()
            standing = screen.error_notice.prompt.window()
            assert standing is not None
            assert [window.alias for window in screen.shown_windows()] == [standing.alias]
            assert screen.words(MODULE_FAILED) in screen.error_notice.words()
            assert list(into.iterdir()) == []
            screen.error_notice.dismiss()
            screen.expect(screen.error_notice.is_shown, operator.not_, description="the error gone")

        def the_same_export_then_writes(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_FAMITRACKER)

            written_project(screen, MODULE_EXPORTED, destination)

        screen.scenario(start_the_module_export, the_folder_refuses_the_file, the_same_export_then_writes).run()
