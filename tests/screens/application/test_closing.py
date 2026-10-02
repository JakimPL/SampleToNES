import operator
from typing import Final, List

import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.paths.extensions import EXT_FILE_MODULE
from sampletones_shared.paths.user import PROJECTS_DIRECTORY, RECONSTRUCTIONS_DIRECTORY
from tests.suite.screens.application import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.holds import ConversionHold, ExportHold, RegenerationHold, ScanHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds import Recording
from tests.suite.screens.steps.main import gather, home_path
from tests.suite.screens.steps.project import retitle_project, save_project_as, saved_project_title
from tests.suite.screens.steps.reconstructions import expect_open, raise_the_first_level_while_held
from tests.suite.screens.views.prompts import Prompt
from tests.suite.screens.world import (
    ARRANGED_PROJECT,
    BASS,
    OPEN_RECONSTRUCTION,
    PLAYABLE_RECONSTRUCTION,
    SONG,
    World,
    documents_world,
    lived_in_world,
    playing_world,
    sequencer_world,
)
from tests.suite.screens.written import written_state

PROJECT_FILENAME: Final[str] = "Closing.stp"
SAVED_TITLE: Final[str] = "Before closing"
NEW_TITLE: Final[str] = "Closing title"
CONVERSION_RUNNING: Final[str] = "global.dialog.message.exit_conversion_in_progress"
PAUSE: Final[str] = "global.menu.label.item_playback_pause"
RUN_TIMEOUT_SECONDS: Final[float] = 60.0
SETTLING_FRAMES: Final[int] = 30
FOLDER: Final[str] = "Many"
FOLDER_RECORDINGS: Final[int] = 130
RECORDING_SECONDS: Final[float] = 0.05
RECORDING_FREQUENCY: Final[float] = 330.0
SCAN_PROGRESS: Final[str] = "main.converter.template.scan_progress"


def save_a_titled_project(screen: Screen) -> None:
    screen.project.create()
    retitle_project(screen, SAVED_TITLE)
    save_project_as(screen, PROJECTS_DIRECTORY / PROJECT_FILENAME)


def change_the_title(screen: Screen) -> None:
    retitle_project(screen, NEW_TITLE)


def close_asks_first(screen: Screen) -> None:
    screen.close_window()

    screen.expect(screen.project.unsaved_prompt.is_shown, bool, description="the unsaved project prompt")


def saved_title() -> str:
    return saved_project_title(PROJECTS_DIRECTORY / PROJECT_FILENAME)


class TestClosingTheWindow:
    """The close button on the window's title bar leaves the application the way Exit does."""

    def test_an_application_with_nothing_unsaved_leaves_at_once(self, screen: Screen) -> None:
        screen.close_window()

        assert screen.wait_for_exit()


class TestClosingTheWindowOverAnUnsavedProject:
    """Closing the window with an unsaved project asks about it first, and asks again at each close."""

    def test_save_writes_the_change_and_leaves(self, screen: Screen) -> None:
        def save_and_leave(screen: Screen) -> None:
            screen.project.unsaved_prompt.save()

            assert screen.wait_for_exit()
            assert saved_title() == NEW_TITLE

        screen.scenario(
            save_a_titled_project,
            change_the_title,
            close_asks_first,
            save_and_leave,
        ).run()

    def test_cancel_keeps_the_application_and_the_file_and_the_next_close_asks_again(self, screen: Screen) -> None:
        prompt = screen.project.unsaved_prompt

        def cancel(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the prompt gone")

        def close_again(screen: Screen) -> None:
            screen.close_window()

            screen.expect(prompt.is_shown, bool, description="the unsaved project prompt again")
            assert len(prompt.shown_windows()) == 1
            assert screen.is_running()
            assert saved_title() == SAVED_TITLE

        def discard_and_leave(screen: Screen) -> None:
            prompt.confirm()

            assert screen.wait_for_exit()
            assert saved_title() == SAVED_TITLE

        screen.scenario(
            save_a_titled_project,
            change_the_title,
            close_asks_first,
            cancel,
            close_again,
            discard_and_leave,
        ).run()


def conversion_question(screen: Screen) -> Prompt:
    """The question exiting asks while a conversion runs, told apart from the reconstruction's by its words."""
    return screen.reconstructions.unsaved_prompt


def asks_about_the_conversion(screen: Screen) -> bool:
    prompt = conversion_question(screen)
    return prompt.is_shown() and screen.words(CONVERSION_RUNNING) in prompt.words()


def close_and_leave(screen: Screen, tab: Tab) -> None:
    """Closes the window with ``tab`` in front, waits for the application to stop, and checks the session written."""
    screen.close_window()

    assert screen.wait_for_exit()
    assert written_state().current.tab is tab


class TestClosingWhilePlaying:
    """Closing the window while a reconstruction plays leaves at once, quietly, and writes the session."""

    @pytest.fixture
    def world(self) -> World:
        return playing_world()

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_it_leaves_while_the_sound_goes_on(self, screen: Screen) -> None:
        def play(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            screen.press_shortcut(ShortcutId.PLAY)
            screen.expect(screen.sequencer.playback.play_entry, screen.words(PAUSE).__eq__, description="playing")
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)

        def close(screen: Screen) -> None:
            close_and_leave(screen, Tab.INSTRUCTIONS)

        screen.scenario(play, close).run()


class TestClosingDuringAConversion:
    """Closing the window while a conversion runs asks first: Cancel keeps both going, Exit stops the run and leaves,
    writing nothing for it.
    """

    @pytest.fixture
    def world(self) -> World:
        return documents_world()

    def test_it_asks_and_then_stops_the_run(self, screen: Screen, conversion_hold: ConversionHold) -> None:
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
    """Closing the window while a folder is read leaves, the read given up, quietly, and writes the session."""

    @pytest.fixture
    def world(self) -> World:
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

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: a folder read outliving the exit calls DearPyGui after its context is gone",
    )
    def test_it_leaves_the_read_behind(self, screen: Screen, scan_hold: ScanHold) -> None:
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
    """Closing the window while an export runs leaves, the export stopped with no file written."""

    @pytest.fixture
    def world(self) -> World:
        return sequencer_world()

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=ARRANGED_PROJECT)

    def test_it_leaves_and_writes_nothing(self, screen: Screen, export_hold: ExportHold) -> None:
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
    """Closing the window while an edit is on its way waits for it to land, then asks about the edited document."""

    @pytest.fixture
    def world(self) -> World:
        return documents_world()

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_it_waits_and_then_asks(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
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


class TestExitWithEverythingPending:
    """Exit with an unsaved project, an unsaved reconstruction and a conversion running asks about each, in that
    order, and leaves once the last is answered.
    """

    @pytest.fixture
    def world(self) -> World:
        return documents_world()

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=SONG)

    def test_the_questions_come_in_order(
        self,
        screen: Screen,
        conversion_hold: ConversionHold,
        regeneration_hold: RegenerationHold,
    ) -> None:
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
