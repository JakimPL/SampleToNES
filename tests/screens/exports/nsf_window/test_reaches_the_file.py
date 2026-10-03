from pathlib import Path
from typing import Final, List

import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_core.constants.enums import ALL_CHANNELS, ChannelName
from sampletones_core.exports.request import ProjectExport
from sampletones_core.project import ProjectContainer
from sampletones_core.timing import SONG_TICK_BOUNDS, SongTiming
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.export.backend import NSFBackend
from sampletones_player.export.program import NSFProgram
from sampletones_player.nsf.information import NSFInformation
from sampletones_shared.application import SAMPLETONES_COPYRIGHT
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from tests.screens.exports.nsf_window.constants import LEFT_OUT, SETTLING_FRAMES
from tests.screens.exports.nsf_window.steps import folder
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.vocabulary.exports import NSF_EXPORTED, NSF_TYPE
from tests.suite.screens.worlds.songs import LOOPING_PROJECT

NSF_TITLE: Final[str] = "global.dialog.title.export_nsf_project"
FROM_THE_START: Final[str] = "settings.nsf.label.repeat_from_start"
FROM_A_FRAME: Final[str] = "settings.nsf.label.repeat_from_frame"
HELD_SOUNDS: Final[str] = "settings.nsf.label.scheme_runs"
FULL_SEARCH: Final[str] = "settings.nsf.label.scheme_search"
TYPED_TITLE: Final[str] = "Rainy Day"
SECOND_FRAME: Final[str] = "01"
LOOP_FRAME: Final[int] = 1


def write_chosen_program(destination: Path) -> None:
    """Writes the program the window is set to in the scenario: noise left out, a repeat from the second frame,
    held sounds stored once and the typed title, the rest as the project states it.
    """
    project = ProjectContainer.load(LOOPING_PROJECT)
    program = NSFProgram(
        information=NSFInformation(
            title=TYPED_TITLE,
            artist=project.info.author,
            copyright=SAMPLETONES_COPYRIGHT,
        ),
        channels=ALL_CHANNELS - {LEFT_OUT},
        loop_tick=SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS).frame_tick(LOOP_FRAME),
        scheme=CompressionScheme.RUNS,
    )
    NSFBackend.stated().choosing(program).write_project(destination, ProjectExport(project=project))


def write_stated_program(destination: Path) -> None:
    """Writes the program the project states for itself, the one the window opens on."""
    project = ProjectContainer.load(LOOPING_PROJECT)
    NSFBackend.stated().choosing(NSFProgram.for_project(project)).write_project(
        destination,
        ProjectExport(project=project),
    )


class TestTheWindowReachesTheFile:
    """Each choice made in the NSF window reaches the program it writes; with every channel unticked, Export waits.

    The window opens on the project's own setup. The scenario unticks every channel, ticks all but noise, sets
    the repeat, the level and the title, picks the file and presses Export. The file equals the program built from
    those choices and differs from the program the project states.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=LOOPING_PROJECT)

    def test_the_program_written_is_the_one_set_up(self, screen: Screen) -> None:
        window = screen.exports.nsf
        into = folder("program")
        destination = into / f"{LOOPING_PROJECT.stem}{EXT_FILE_NSF}"
        asked: List[int] = []

        def open_the_window(screen: Screen) -> None:
            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_NSF)

            screen.expect(window.is_shown, bool, description="the NSF window")
            assert all(window.offers(channel) and window.is_ticked(channel) for channel in ChannelName.items())
            assert window.repeat() == screen.words(FROM_THE_START)
            assert window.level() == screen.words(FULL_SEARCH)
            assert not window.says_a_channel_is_needed()
            asked.append(len(screen.dialog_requests()))

        def with_no_channel_export_waits(screen: Screen) -> None:
            for channel in ChannelName.items():
                window.tick(channel)

            screen.expect(window.says_a_channel_is_needed, bool, description="the window asking for a channel")
            assert not window.can_export()
            window.press_export()
            screen.frames(SETTLING_FRAMES)
            assert window.is_shown()
            assert len(screen.dialog_requests()) == asked[0]
            assert list(into.iterdir()) == []

        def a_channel_ticked_lets_it_go(screen: Screen) -> None:
            for channel in ChannelName.items():
                if channel != LEFT_OUT:
                    window.tick(channel)

            screen.expect(window.can_export, bool, description="Export answering")
            assert not window.says_a_channel_is_needed()
            assert not window.is_ticked(LEFT_OUT)

        def set_the_repeat_the_level_and_the_title(screen: Screen) -> None:
            window.choose_repeat(screen.words(FROM_A_FRAME))
            window.type_loop_frame(SECOND_FRAME)
            window.choose_level(screen.words(HELD_SOUNDS))
            window.type_title(TYPED_TITLE)

            screen.expect(window.title, TYPED_TITLE.__eq__, description="the title typed")
            assert window.repeat() == screen.words(FROM_A_FRAME)
            assert window.loop_frame() == SECOND_FRAME
            assert window.level() == screen.words(HELD_SOUNDS)

        def choose_the_file(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            window.browse()

            screen.expect(lambda: len(screen.dialog_requests()), (asked[0] + 1).__eq__, description="the file asked")
            request = screen.dialog_requests()[-1]
            assert request.title == screen.words(NSF_TITLE)
            assert request.suggested_name == destination.name
            assert [file_filter.name for file_filter in request.filters] == [screen.words(NSF_TYPE)]

        def the_program_written_is_the_one_set_up(screen: Screen) -> None:
            notice = screen.exports.project_notice

            window.export()

            screen.expect(notice.is_shown, bool, description="the program written")
            assert screen.words(NSF_EXPORTED) in notice.words()
            assert not window.is_shown()
            notice.dismiss()
            chosen = folder("chosen") / destination.name
            stated = folder("stated") / destination.name
            write_chosen_program(chosen)
            write_stated_program(stated)
            assert destination.read_bytes() == chosen.read_bytes()
            assert destination.read_bytes() != stated.read_bytes()

        screen.scenario(
            open_the_window,
            with_no_channel_export_waits,
            a_channel_ticked_lets_it_go,
            set_the_repeat_the_level_and_the_title,
            choose_the_file,
            the_program_written_is_the_one_set_up,
        ).run()
