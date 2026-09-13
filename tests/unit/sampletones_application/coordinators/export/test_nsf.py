from pathlib import Path
from typing import Any, Dict, Final, List, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.export import nsf as nsf_module
from sampletones_application.coordinators.export.nsf import NSFExportCoordinator
from sampletones_application.logic.export.nsf.logic import NSFExportLogic
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.view import NSFExportViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from sampletones_shared.types.callback import VoidCallback
from tests.suite.language import FakeLanguageManager
from tests.suite.nsf import FakeNSFExportService, FakeProgramBackend
from tests.suite.player import player_sample

PROJECT_FILE: Final[Path] = Path("/home/user/projects/chiptune.stp")
PROJECT_DIRECTORY: Final[Path] = PROJECT_FILE.parent
INSTRUMENT_DIRECTORY: Final[Path] = Path("/home/user/instruments")
PROJECT_NAME: Final[str] = "chiptune"
SAMPLE_NAME: Final[str] = "Amen"
NTSC_FREQUENCY: Final[int] = 60
CHOSEN: Final[Path] = Path("/home/user/programs/take one.nsf")


class _WindowRecorder:
    """Stands in for the NSF export dialog, holding what it was told to show."""

    def __init__(self) -> None:
        self.view_models: List[NSFExportViewModel] = []
        self.visible = False
        self.hides = 0
        self.on_choices_changed: Any = None
        self.on_browse: Any = None
        self.on_export: Any = None
        self.on_close: Any = None

    def open(self, view_model: NSFExportViewModel) -> None:
        self.visible = True
        self.view_models.append(view_model)

    def update_view(self, view_model: NSFExportViewModel) -> None:
        self.view_models.append(view_model)

    def hide(self) -> None:
        self.hides += 1
        self.visible = False

    @property
    def view(self) -> NSFExportViewModel:
        assert self.view_models, "A view was expected to reach the window"
        return self.view_models[-1]


class _SaveDialogRecorder:
    """The OS save dialog as the coordinator asks it, answering with a stated path."""

    def __init__(self) -> None:
        self.answer: Optional[Path] = CHOSEN
        self.requests: List[Dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> Optional[Path]:
        self.requests.append(kwargs)
        return self.answer

    @property
    def filters(self) -> List[FileFilter]:
        assert self.requests, "A destination was expected to be asked for"
        return list(self.requests[-1]["filters"])


class NSFExportFixture:
    """The coordinator over a real setup logic, a recording service and backend, and a recorded screen.

    The frame the hand-over waits for passes when a test asks for it, so the step from the dialog
    leaving the screen to the run starting is walked one frame at a time.
    """

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        operation_active: bool = False,
    ) -> None:
        project_manager = ProjectManager()
        project_manager.session.mark_loaded(PROJECT_NAME)
        self.controller = ProjectController(project_manager)
        self.session_manager = MagicMock()
        self.session_manager.get_project_path.return_value = PROJECT_FILE
        self.session_manager.get_instrument_path.return_value = INSTRUMENT_DIRECTORY
        self.service = FakeNSFExportService()
        self.backend = FakeProgramBackend()
        self.logic = NSFExportLogic(
            self.controller,
            self.session_manager,
            self.service,
            self.backend,
            is_operation_active=lambda: operation_active,
        )

        self.window = _WindowRecorder()
        self.save_dialog = _SaveDialogRecorder()
        self.activity = 0
        self.pending: List[VoidCallback] = []

        monkeypatch.setattr(nsf_module, "save_file_dialog", self.save_dialog)
        monkeypatch.setattr(
            nsf_module.FrameCallbackManager,
            "set_frame_callback",
            lambda callback, frame_count=1: self.pending.append(callback),
        )

        self.coordinator = NSFExportCoordinator(
            self.logic,
            window=self.window,  # type: ignore[arg-type]
            language_manager=FakeLanguageManager(),  # type: ignore[arg-type]
            on_activity_changed=self._on_activity_changed,
        )

    def _on_activity_changed(self) -> None:
        self.activity += 1

    def edit(self, choices: NSFExportChoices) -> None:
        self.window.on_choices_changed(choices)

    def browse(self) -> None:
        self.window.on_browse()

    def export(self) -> None:
        self.window.on_export()

    def close(self) -> None:
        self.window.on_close()

    def advance_frame(self) -> None:
        pending = self.pending
        self.pending = []
        for callback in pending:
            callback()


@pytest.fixture
def nsf(monkeypatch: pytest.MonkeyPatch) -> NSFExportFixture:
    return NSFExportFixture(monkeypatch)


class TestOfferingTheSetup:
    def test_a_project_opens_the_dialog_over_its_setup(self, nsf: NSFExportFixture) -> None:
        nsf.coordinator.open_project()

        assert nsf.window.visible
        assert nsf.window.view.destination == PROJECT_DIRECTORY / f"{PROJECT_NAME}{EXT_FILE_NSF}"

    def test_a_reconstruction_opens_the_dialog_over_its_slices(self, nsf: NSFExportFixture) -> None:
        nsf.coordinator.open_sample(player_sample(SAMPLE_NAME, (), nes_frequency=NTSC_FREQUENCY))

        assert nsf.window.visible
        assert nsf.window.view.destination == INSTRUMENT_DIRECTORY / f"{SAMPLE_NAME}{EXT_FILE_NSF}"

    def test_opening_claims_the_application(self, nsf: NSFExportFixture) -> None:
        nsf.coordinator.open_project()

        assert nsf.coordinator.is_active
        assert nsf.activity == 1

    def test_another_exclusive_operation_leaves_the_dialog_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        nsf = NSFExportFixture(monkeypatch, operation_active=True)

        nsf.coordinator.open_project()

        assert not nsf.window.visible
        assert not nsf.activity

    def test_closing_the_setup_hands_the_application_back(self, nsf: NSFExportFixture) -> None:
        nsf.coordinator.open_project()

        nsf.close()

        assert nsf.window.hides == 1
        assert not nsf.coordinator.is_active
        assert nsf.activity == 2
        assert not nsf.service.projects


class TestTheEditsTheDialogReports:
    def test_an_edit_comes_back_to_the_window(self, nsf: NSFExportFixture) -> None:
        nsf.coordinator.open_project()
        view = nsf.window.view

        nsf.edit(view.choices.with_channel(ChannelName.NOISE, False, view.offer))

        assert not nsf.window.view.channel_sounded(ChannelName.NOISE)


class TestAskingForTheDestination:
    def test_the_file_is_asked_for_from_where_it_stands(self, nsf: NSFExportFixture) -> None:
        nsf.coordinator.open_project()

        nsf.browse()

        request = nsf.save_dialog.requests[-1]
        assert request["initial_directory"] == PROJECT_DIRECTORY
        assert request["default_filename"] == f"{PROJECT_NAME}{EXT_FILE_NSF}"
        assert [file_filter.extensions for file_filter in nsf.save_dialog.filters] == [(EXT_FILE_NSF,)]

    def test_a_chosen_file_becomes_the_one_the_export_writes(self, nsf: NSFExportFixture) -> None:
        nsf.coordinator.open_project()

        nsf.browse()

        assert nsf.window.view.destination == CHOSEN

    def test_a_dismissed_dialog_leaves_the_file_alone(self, nsf: NSFExportFixture) -> None:
        nsf.coordinator.open_project()
        nsf.save_dialog.answer = None
        standing = nsf.window.view.destination

        nsf.browse()

        assert nsf.window.view.destination == standing


class TestHandingTheExportOver:
    def test_the_dialog_leaves_the_screen_before_the_run_starts(self, nsf: NSFExportFixture) -> None:
        nsf.coordinator.open_project()

        nsf.export()

        assert nsf.window.hides == 1
        assert not nsf.service.projects
        assert nsf.coordinator.is_active

    def test_the_run_starts_once_that_frame_has_finished(self, nsf: NSFExportFixture) -> None:
        nsf.coordinator.open_project()
        destination = nsf.window.view.destination
        nsf.export()

        nsf.advance_frame()

        assert [run.destination for run in nsf.service.projects] == [destination]
        assert not nsf.coordinator.is_active
        assert nsf.activity == 2

    def test_the_run_writes_the_program_the_dialog_stood_at(self, nsf: NSFExportFixture) -> None:
        nsf.coordinator.open_project()
        view = nsf.window.view
        nsf.edit(view.choices.with_channel(ChannelName.NOISE, False, view.offer))
        nsf.export()

        nsf.advance_frame()

        assert ChannelName.NOISE not in nsf.backend.program.channels
