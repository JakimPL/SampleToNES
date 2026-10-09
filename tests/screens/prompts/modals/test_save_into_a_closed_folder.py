import operator
import stat
from typing import Final

import pytest

from automation.application.startup import Startup
from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from automation.steps.reconstructions import expect_open, marked, remove_from_the_browser, titled
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.screens.prompts.modals.constants import SETTLING_FRAMES
from tests.suite.screens.worlds.recordings import OPEN_RECONSTRUCTION

KEPT: Final[str] = "Kept.stn"
LOCKED_FOLDER: Final[str] = "Locked"
READ_AND_ENTER: Final[int] = stat.S_IRUSR | stat.S_IXUSR
SAVE_FAILED: Final[str] = "global.dialog.message.reconstruction_save_failed"


class TestASaveIntoAFolderThatTakesNothing:
    """A save into a folder that accepts no file shows its failure alone, and the reconstruction stays open.

    The open reconstruction loses its file and a read-only folder is made. Close asks, Save into the folder
    fails, and the failure shows alone. Dismissing it keeps the reconstruction open, and a save into a
    writable folder closes it.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """Opens a reconstruction with no project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_the_failure_stands_alone_and_a_save_elsewhere_closes_it(self, screen: Screen) -> None:
        """The failure shows alone, and a save elsewhere writes the file and closes the reconstruction."""
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt
        notice = screen.error_notice
        locked = RECONSTRUCTIONS_DIRECTORY / LOCKED_FOLDER
        kept = RECONSTRUCTIONS_DIRECTORY / KEPT

        def remove_its_file(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            locked.mkdir()
            locked.chmod(READ_AND_ENTER)

            remove_from_the_browser(screen, OPEN_RECONSTRUCTION)

            screen.expect(
                screen.title,
                titled(screen, marked(OPEN_RECONSTRUCTION.name, unsaved=True)).__eq__,
                description="the reconstruction left unsaved",
            )

        def save_into_the_locked_folder(screen: Screen) -> None:
            reconstructions.close_from_menu()
            screen.expect(prompt.is_shown, bool, description="the question about closing")
            screen.answer_next_dialog(DialogKind.SAVE, locked / KEPT)

            prompt.save()

            screen.expect(notice.is_shown, bool, description="the failure reported")
            screen.claim_error(PermissionError.__name__)
            assert screen.words(SAVE_FAILED) in notice.words()
            screen.frames(SETTLING_FRAMES)
            assert not prompt.is_shown()
            assert len(screen.shown_windows()) == 1

        def dismissing_it_leaves_the_reconstruction_open(screen: Screen) -> None:
            notice.dismiss()

            screen.expect(notice.is_shown, operator.not_, description="the failure dismissed")
            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()
            assert screen.title() == titled(screen, marked(OPEN_RECONSTRUCTION.name, unsaved=True))
            assert not (locked / KEPT).exists()

        def a_save_elsewhere_closes_it(screen: Screen) -> None:
            reconstructions.close_from_menu()
            screen.expect(prompt.is_shown, bool, description="the question again")
            screen.answer_next_dialog(DialogKind.SAVE, kept)

            prompt.save()

            screen.expect(screen.title, titled(screen).__eq__, description="the reconstruction closed")
            assert kept.exists()

        screen.scenario(
            remove_its_file,
            save_into_the_locked_folder,
            dismissing_it_leaves_the_reconstruction_open,
            a_save_elsewhere_closes_it,
        ).run()
