from pathlib import Path
from typing import Final, List

import pytest

from automation.application.startup import Startup
from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from automation.vocabulary.exports import ROM_EXPORTED, ROM_TYPE
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import ProjectExport
from sampletones_core.project import ProjectContainer
from sampletones_player.export.backends import program_backends
from sampletones_player.export.program import Program
from sampletones_player.information import ProgramInformation
from sampletones_shared.paths.extensions import EXT_FILE_ROM
from tests.screens.exports.nsf_window.steps import folder
from tests.suite.screens.worlds.songs import LOOPING_PROJECT

ROM_TITLE: Final[str] = "global.dialog.title.export_rom_project"
TYPED_TITLE: Final[str] = "Sunny Beach"


def write_titled_program(destination: Path) -> None:
    """Writes the program the project states for itself, under the typed title."""
    project = ProjectContainer.load(LOOPING_PROJECT)
    stated = Program.for_project(project)
    information = ProgramInformation(
        title=TYPED_TITLE,
        artist=stated.information.artist,
        copyright=stated.information.copyright,
    )
    program = stated.model_copy(update={"information": information})
    program_backends()[ExportFormat.ROM].choosing(program).write_project(destination, ProjectExport(project=project))


class TestTheWindowReachesTheCartridge:
    """The program window opened for a cartridge writes the cartridge set up in it.

    The scenario opens the window from **NES ROM...**, types a title, picks the file and presses Export. The file
    equals the cartridge built from the project under that title.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=LOOPING_PROJECT)

    def test_the_cartridge_written_is_the_one_set_up(self, screen: Screen) -> None:
        window = screen.exports.nsf
        into = folder("cartridge")
        destination = into / f"{LOOPING_PROJECT.stem}{EXT_FILE_ROM}"
        asked: List[int] = []

        def open_the_window(screen: Screen) -> None:
            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_ROM)

            screen.expect(window.is_shown, bool, description="the program window")
            asked.append(len(screen.dialog_requests()))

        def type_the_title(screen: Screen) -> None:
            window.type_title(TYPED_TITLE)

            screen.expect(window.title, TYPED_TITLE.__eq__, description="the title typed")

        def choose_the_file(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            window.browse()

            screen.expect(lambda: len(screen.dialog_requests()), (asked[0] + 1).__eq__, description="the file asked")
            request = screen.dialog_requests()[-1]
            assert request.title == screen.words(ROM_TITLE)
            assert request.suggested_name == destination.name
            assert [file_filter.name for file_filter in request.filters] == [screen.words(ROM_TYPE)]

        def the_cartridge_written_is_the_one_set_up(screen: Screen) -> None:
            notice = screen.exports.project_notice

            window.export()

            screen.expect(notice.is_shown, bool, description="the cartridge written")
            assert screen.words(ROM_EXPORTED) in notice.words()
            notice.dismiss()
            expected = folder("titled") / destination.name
            write_titled_program(expected)
            assert destination.read_bytes() == expected.read_bytes()

        screen.scenario(
            open_the_window,
            type_the_title,
            choose_the_file,
            the_cartridge_written_is_the_one_set_up,
        ).run()
