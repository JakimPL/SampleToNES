import operator
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
from sampletones_player.specification.nsf import NSF_MAGIC
from sampletones_shared.application import SAMPLETONES_COPYRIGHT
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from tests.suite.screens.application import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import expect_open
from tests.suite.screens.world import LOOPING_PROJECT, PLAYABLE_RECONSTRUCTION

NSF_TITLE: Final[str] = "global.dialog.title.export_nsf_project"
NSF_TYPE: Final[str] = "global.dialog.filter.nsf"
NSF_EXPORTED: Final[str] = "global.dialog.message.nsf_project_exported_successfully"
INSTRUMENTS_EXPORTED: Final[str] = "reconstructions.instruments.message.export_instruments_success"
NO_CHANNEL: Final[str] = "settings.nsf.message.no_channel"
FROM_THE_START: Final[str] = "settings.nsf.label.repeat_from_start"
FROM_A_FRAME: Final[str] = "settings.nsf.label.repeat_from_frame"
HELD_SOUNDS: Final[str] = "settings.nsf.label.scheme_runs"
FULL_SEARCH: Final[str] = "settings.nsf.label.scheme_search"
TYPED_TITLE: Final[str] = "Rainy Day"
SECOND_FRAME: Final[str] = "01"
LOOP_FRAME: Final[int] = 1
LEFT_OUT: Final[ChannelName] = ChannelName.NOISE
SILENT_IN_THE_RECONSTRUCTION: Final[ChannelName] = ChannelName.PULSE2
SETTLING_FRAMES: Final[int] = 20


def folder(name: str) -> Path:
    """A folder of the home for the program, standing on the disk as a native dialog's answer does."""
    path = Path.cwd() / "exports" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_chosen_program(destination: Path) -> None:
    """Writes the program the window is set to in the scenario: noise left out, a repeat from the second frame, held sounds
    stored once, and the typed title, the rest as the project states it.
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
    """Each choice made in the NSF window reaches the program it writes; with no channel ticked, Export waits."""

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


class TestAReconstructionsSilentChannels:
    """A reconstruction's program offers the channels it sounds alone: a silent channel's box is greyed and a press on
    it ticks nothing.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_a_silent_channel_stays_out(self, screen: Screen) -> None:
        window = screen.exports.nsf
        destination = folder("reconstruction") / f"{PLAYABLE_RECONSTRUCTION.stem}{EXT_FILE_NSF}"
        sounding = [channel for channel in ChannelName.items() if channel != SILENT_IN_THE_RECONSTRUCTION]

        def open_the_window(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)

            screen.exports.export_reconstruction(MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_NSF)

            screen.expect(window.is_shown, bool, description="the NSF window")
            assert not window.offers(SILENT_IN_THE_RECONSTRUCTION)
            assert not window.is_ticked(SILENT_IN_THE_RECONSTRUCTION)
            assert all(window.offers(channel) and window.is_ticked(channel) for channel in sounding)

        def a_press_on_the_silent_channel_ticks_nothing(screen: Screen) -> None:
            window.press_on(SILENT_IN_THE_RECONSTRUCTION)

            screen.frames(SETTLING_FRAMES)
            assert not window.is_ticked(SILENT_IN_THE_RECONSTRUCTION)

        def a_press_on_a_sounding_channel_lets_it_go_and_back(screen: Screen) -> None:
            window.tick(LEFT_OUT)
            screen.expect(lambda: window.is_ticked(LEFT_OUT), operator.not_, description="the noise let go")

            window.tick(LEFT_OUT)

            screen.expect(lambda: window.is_ticked(LEFT_OUT), bool, description="the noise ticked again")
            assert not window.is_ticked(SILENT_IN_THE_RECONSTRUCTION)

        def the_program_is_written(screen: Screen) -> None:
            notice = screen.exports.file_notice
            screen.answer_next_dialog(DialogKind.SAVE, destination)
            window.browse()
            screen.expect(lambda: screen.dialog_requests()[-1].answer == destination, bool, description="the file")

            window.export()

            screen.expect(notice.is_shown, bool, description="the program written")
            assert screen.words(INSTRUMENTS_EXPORTED) in notice.words()
            assert destination.read_bytes().startswith(NSF_MAGIC)
            notice.dismiss()

        screen.scenario(
            open_the_window,
            a_press_on_the_silent_channel_ticks_nothing,
            a_press_on_a_sounding_channel_lets_it_go_and_back,
            the_program_is_written,
        ).run()
