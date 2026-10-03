import operator
from typing import Final

import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.paths.extensions import EXT_FILE_MODULE
from sampletones_shared.paths.user import PROJECTS_DIRECTORY, RECONSTRUCTIONS_DIRECTORY
from tests.screens.application.closing.constants import RUN_TIMEOUT_SECONDS
from tests.screens.application.closing.steps import asks_about_the_conversion, conversion_question
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.holds.conversion import ConversionHold
from tests.suite.screens.holds.export import ExportHold
from tests.suite.screens.holds.regeneration import RegenerationHold
from tests.suite.screens.holds.scan import ScanHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds.recordings import Recording
from tests.suite.screens.steps.main import gather, home_path
from tests.suite.screens.steps.reconstructions import expect_open, raise_the_first_level_while_held
from tests.suite.screens.vocabulary.playback import PAUSE
from tests.suite.screens.worlds.home import World
from tests.suite.screens.worlds.recordings import (
    BASS,
    OPEN_RECONSTRUCTION,
    PLAYABLE_RECONSTRUCTION,
    documents_world,
    lived_in_world,
    playing_world,
)
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT, sequencer_world
from tests.suite.screens.written import written_state

SETTLING_FRAMES: Final[int] = 30
FOLDER: Final[str] = "Many"
FOLDER_RECORDINGS: Final[int] = 130
RECORDING_SECONDS: Final[float] = 0.05
RECORDING_FREQUENCY: Final[float] = 330.0


def close_and_leave(screen: Screen, tab: Tab) -> None:
    """Closes the window with ``tab`` in front, waits for the application to stop, and checks the session
    written.
    """
    screen.close_window()

    assert screen.wait_for_exit()
    assert written_state().current.tab is tab


class TestClosingWhilePlaying:
    """Closing the window while a reconstruction plays leaves at once and writes the session.

    A playable reconstruction is open at start. The scenario presses Play, waits for the Play entry to read
    Pause, brings the Instructions tab forward, closes the window, and expects the application to stop with
    Instructions written as the tab in front.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds a playable reconstruction and a session ready for playback."""
        return playing_world()

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the playable reconstruction at start."""
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_it_leaves_while_the_sound_goes_on(self, screen: Screen) -> None:
        """The window closes at once and the session names the tab in front."""

        def play(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            screen.press_shortcut(ShortcutId.PLAY)
            screen.expect(screen.sequencer.playback.play_entry, screen.words(PAUSE).__eq__, description="playing")
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)

        def close(screen: Screen) -> None:
            close_and_leave(screen, Tab.INSTRUCTIONS)

        screen.scenario(play, close).run()


class TestClosingDuringAConversion:
    """Closing the window while a conversion runs asks first: Cancel keeps both going, Exit stops the run and
    leaves.

    The scenario gathers a recording, presses the converter's action, and waits for progress. The first
    close asks about the run; Cancel takes the question back and leaves the run going. The second close
    asks again; Exit stops the run and leaves, and the session is written with the Main tab in front and no
    reconstruction in the reconstructions folder.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds the documents world: recordings to gather and stored documents."""
        return documents_world()

    def test_it_asks_and_then_stops_the_run(self, screen: Screen, conversion_hold: ConversionHold) -> None:
        """Cancel keeps the run and the application; Exit leaves with the run's output absent."""
        converter = screen.main.converter
        prompt = conversion_question(screen)

        def start_a_held_run(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.MAIN)
            gather(screen, home_path(BASS))
            converter.press_action()
            screen.bridge.expect(
                converter.progress,
                lambda progress: progress > 0,
                description="the run under way",
                timeout=RUN_TIMEOUT_SECONDS,
            )

        def cancel_keeps_it_running(screen: Screen) -> None:
            screen.close_window()
            screen.expect(lambda: asks_about_the_conversion(screen), bool, description="the question about the run")

            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question taken back")
            screen.frames(SETTLING_FRAMES)
            assert screen.is_running()
            assert converter.progress() > 0

        def exit_stops_it_and_leaves(screen: Screen) -> None:
            screen.close_window()
            screen.expect(lambda: asks_about_the_conversion(screen), bool, description="the question again")

            prompt.confirm()

            assert screen.wait_for_exit()
            assert written_state().current.tab is Tab.MAIN
            assert not list(RECONSTRUCTIONS_DIRECTORY.rglob(f"{home_path(BASS).stem}.*"))

        screen.scenario(start_a_held_run, cancel_keeps_it_running, exit_stops_it_and_leaves).run()


class TestClosingDuringAFolderRead:
    """Closing the window while a folder is read leaves, the read given up, and writes the session.

    The home holds a folder of many short recordings. The scenario Ctrl-clicks the folder to start a read,
    waits until the converter shows the scan, closes the window, and expects the application to stop with
    the Main tab written.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds a lived-in session and a folder of many short recordings."""
        lived_in = lived_in_world()
        return World(
            state=lived_in.state,
            application_config=None,
            config=None,
            files=tuple(
                Recording(
                    destination=home_path(FOLDER) / f"take{index:03d}.wav",
                    seconds=RECORDING_SECONDS,
                    frequency=RECORDING_FREQUENCY,
                )
                for index in range(FOLDER_RECORDINGS)
            ),
        )

    def test_it_leaves_the_read_behind(self, screen: Screen, scan_hold: ScanHold) -> None:
        """The application stops after the close while the folder read is in progress."""
        converter = screen.main.converter

        def start_reading(screen: Screen) -> None:
            row = screen.expect_item(
                lambda: screen.explorer.file_row(home_path(FOLDER)),
                description="the folder's row",
            )
            screen.explorer.ctrl_click(row)
            screen.expect(converter.scan_shown, bool, description="the folder being read")

        def close(screen: Screen) -> None:
            close_and_leave(screen, Tab.MAIN)

        screen.scenario(start_reading, close).run()


class TestClosingDuringAnExport:
    """Closing the window while an export runs leaves, the export stopped with no file written.

    An arranged project is open. The scenario starts a FamiTracker export whose writing is held, closes the
    window, and expects the application to stop with the Sequencer tab written and the export's destination
    absent.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds a Sequencer world with an arranged project."""
        return sequencer_world()

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the arranged project at start."""
        return Startup(reconstruction=None, project=ARRANGED_PROJECT)

    def test_it_leaves_and_writes_nothing(self, screen: Screen, export_hold: ExportHold) -> None:
        """The application stops and the export's destination stays absent."""
        destination = PROJECTS_DIRECTORY / f"{ARRANGED_PROJECT.stem}{EXT_FILE_MODULE}"

        def start_a_held_export(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            screen.answer_next_dialog(DialogKind.SAVE, destination)
            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_FAMITRACKER)
            screen.expect(screen.exports.progress.is_shown, bool, description="the export under way")
            screen.expect(export_hold.waiting, (1).__eq__, description="the export held")

        def close(screen: Screen) -> None:
            close_and_leave(screen, Tab.SEQUENCER)

            assert not destination.exists()

        screen.scenario(start_a_held_export, close).run()


class TestClosingDuringARebuild:
    """Closing the window while an edit is on its way waits for it to land, then asks about the edited
    document.

    An open reconstruction receives an edit whose regeneration is held. The first close keeps the
    application running with no question. Once the edit lands, the question about the edited reconstruction
    appears; confirming it leaves.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds the documents world with a reconstruction ready to open."""
        return documents_world()

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the reconstruction at start."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_it_waits_and_then_asks(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        """The close waits for the held edit, then the unsaved reconstruction prompt appears."""
        prompt = screen.reconstructions.unsaved_prompt

        def edit_while_held(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            raise_the_first_level_while_held(screen, regeneration_hold, ChannelName.PULSE1)

        def close_waits_for_the_edit(screen: Screen) -> None:
            screen.close_window()

            screen.frames(SETTLING_FRAMES)
            assert screen.is_running()
            assert not prompt.is_shown()

        def the_edit_lands_and_the_question_comes(screen: Screen) -> None:
            regeneration_hold.release()

            screen.expect(prompt.is_shown, bool, description="the question about the edited reconstruction")
            prompt.confirm()

            assert screen.wait_for_exit()

        screen.scenario(edit_while_held, close_waits_for_the_edit, the_edit_lands_and_the_question_comes).run()
