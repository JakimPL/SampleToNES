from pathlib import Path
from typing import Any, Dict, Final, List, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators import render as render_module
from sampletones_application.coordinators.render import SongRenderCoordinator
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.render.logic import SongRenderLogic
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceSuccess,
)
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.view_model.shared.render import (
    SongRenderSettings,
    SongRenderViewModel,
)
from sampletones_core.audio.writers import AudioFormat
from sampletones_core.configs import Config
from sampletones_shared.types.callback import VoidCallback
from tests.suite.language import FakeLanguageManager
from tests.suite.render import FakeRenderService

AUDIO_DIRECTORY: Final[Path] = Path("/home/user/audio")
PROJECT_NAME: Final[str] = "chiptune"
CHOSEN: Final[Path] = Path("/home/user/renders/take one.wav")


class _WindowRecorder:
    """Stands in for the render dialog, holding what it was told to show."""

    def __init__(self) -> None:
        self.view_models: List[SongRenderViewModel] = []
        self.visible = False
        self.hides = 0
        self.on_settings_changed: Any = None
        self.on_browse: Any = None
        self.on_render: Any = None
        self.on_cancel: Any = None
        self.on_close: Any = None

    def open(self, view_model: SongRenderViewModel) -> None:
        self.visible = True
        self.view_models.append(view_model)

    def update_view(self, view_model: SongRenderViewModel) -> None:
        self.view_models.append(view_model)

    def hide(self) -> None:
        self.hides += 1
        self.visible = False

    @property
    def view(self) -> SongRenderViewModel:
        assert self.view_models, "A view was expected to reach the window"
        return self.view_models[-1]


class _DialogsRecorder:
    def __init__(self) -> None:
        self.paths: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def show_message_with_path(self, title: str, message: str, path: Path) -> None:
        self.paths.append({"title": title, "message": message, "path": path})

    def show_error(self, exception: Exception, message: Optional[str] = None) -> None:
        self.errors.append({"exception": exception, "message": message})


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


class RenderFixture:
    """The coordinator over a real render logic, a recording service, and a recorded screen.

    The frame the report waits for is taken as passing when a test asks for it, so the hand-off
    from the window to the dialog that reports an outcome is walked one step at a time.
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
        self.session_manager.get_audio_path.return_value = AUDIO_DIRECTORY
        self.service = FakeRenderService()
        self.logic = SongRenderLogic(
            self.controller,
            MagicMock(config=Config()),
            self.session_manager,
            self.service,
            language_manager=FakeLanguageManager(),  # type: ignore[arg-type]
            is_operation_active=lambda: operation_active,
        )

        self.window = _WindowRecorder()
        self.dialogs = _DialogsRecorder()
        self.save_dialog = _SaveDialogRecorder()
        self.activity = 0
        self.pending: List[VoidCallback] = []

        monkeypatch.setattr(render_module, "save_file_dialog", self.save_dialog)
        monkeypatch.setattr(
            render_module.FrameCallbackManager,
            "set_frame_callback",
            lambda callback, frame_count=1: self.pending.append(callback),
        )

        self.coordinator = SongRenderCoordinator(
            self.logic,
            window=self.window,  # type: ignore[arg-type]
            dialogs=self.dialogs,  # type: ignore[arg-type]
            language_manager=FakeLanguageManager(),  # type: ignore[arg-type]
            on_activity_changed=self._on_activity_changed,
        )

    def _on_activity_changed(self) -> None:
        self.activity += 1

    def open(self) -> None:
        self.coordinator.open()

    def edit(self, settings: SongRenderSettings) -> None:
        self.window.on_settings_changed(settings)

    def browse(self) -> None:
        self.window.on_browse()

    def start(self) -> None:
        self.window.on_render()

    def stop(self) -> None:
        self.window.on_cancel()

    def close(self) -> None:
        self.window.on_close()

    def advance_frame(self) -> None:
        """Runs what was waiting for the frame the window left the screen in."""
        pending = self.pending
        self.pending = []
        for callback in pending:
            callback()


@pytest.fixture
def render(monkeypatch: pytest.MonkeyPatch) -> RenderFixture:
    return RenderFixture(monkeypatch)


class TestOfferingTheRender:
    def test_the_dialog_opens_over_the_render_being_set_up(self, render: RenderFixture) -> None:
        render.open()

        assert render.window.visible
        assert render.window.view.destination == AUDIO_DIRECTORY / f"{PROJECT_NAME}.wav"

    def test_opening_claims_the_application(self, render: RenderFixture) -> None:
        render.open()

        assert render.coordinator.is_active
        assert render.activity == 1

    def test_another_exclusive_operation_leaves_the_dialog_closed(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        render = RenderFixture(monkeypatch, operation_active=True)

        render.open()

        assert not render.window.visible
        assert not render.window.view_models
        assert not render.activity

    def test_closing_the_setup_hands_the_application_back(self, render: RenderFixture) -> None:
        render.open()

        render.close()

        assert render.window.hides == 1
        assert not render.coordinator.is_active
        assert render.activity == 2


class TestTheEditsTheDialogReports:
    def test_an_edit_comes_back_reconciled(self, render: RenderFixture) -> None:
        render.open()

        render.edit(render.window.view.settings.with_format(AudioFormat.MP3))

        assert render.window.view.spec.audio_format == AudioFormat.MP3
        assert render.window.view.destination == AUDIO_DIRECTORY / f"{PROJECT_NAME}.mp3"

    def test_the_running_render_reaches_the_window(self, render: RenderFixture) -> None:
        render.open()
        render.start()

        render.service.emit(ServiceSuccess(value=CHOSEN))

        assert render.window.view.progress == 1.0


class TestAskingForTheDestination:
    def test_the_file_is_asked_for_from_where_it_stands(self, render: RenderFixture) -> None:
        render.open()

        render.browse()

        request = render.save_dialog.requests[-1]
        assert request["initial_directory"] == AUDIO_DIRECTORY
        assert request["default_filename"] == f"{PROJECT_NAME}.wav"

    def test_the_type_offered_is_the_container_standing(self, render: RenderFixture) -> None:
        render.open()
        render.edit(render.window.view.settings.with_format(AudioFormat.MP3))

        render.browse()

        assert [file_filter.extensions for file_filter in render.save_dialog.filters] == [(".mp3",)]

    def test_a_chosen_file_becomes_the_one_the_render_writes(self, render: RenderFixture) -> None:
        render.open()

        render.browse()

        assert render.window.view.destination == CHOSEN
        render.session_manager.set_audio_path.assert_called_once_with(CHOSEN)

    def test_a_dismissed_dialog_leaves_the_file_alone(self, render: RenderFixture) -> None:
        render.open()
        render.save_dialog.answer = None
        standing = render.window.view.destination

        render.browse()

        assert render.window.view.destination == standing


class TestDrivingTheRender:
    def test_the_start_reaches_the_service(self, render: RenderFixture) -> None:
        render.open()

        render.start()

        assert render.service.request.destination == AUDIO_DIRECTORY / f"{PROJECT_NAME}.wav"

    def test_the_stop_reaches_the_service(self, render: RenderFixture) -> None:
        render.open()
        render.start()

        render.stop()

        assert render.service.cancels == 1

    def test_exit_winds_a_running_render_down(self, render: RenderFixture) -> None:
        render.open()
        render.start()

        render.coordinator.cleanup()

        assert render.service.shutdowns == 1


class TestReportingTheOutcome:
    def test_a_finished_render_reports_the_file_it_wrote(self, render: RenderFixture) -> None:
        render.open()
        render.start()

        render.service.emit(ServiceSuccess(value=CHOSEN))
        render.advance_frame()

        assert render.dialogs.paths == [
            {
                "title": "settings.render.title.rendered",
                "message": "settings.render.message.rendered",
                "path": CHOSEN,
            }
        ]

    def test_the_report_waits_for_the_screen_the_window_left(self, render: RenderFixture) -> None:
        render.open()
        render.start()

        render.service.emit(ServiceSuccess(value=CHOSEN))

        assert render.window.hides == 1
        assert not render.dialogs.paths

    def test_a_failed_render_reports_what_went_wrong(self, render: RenderFixture) -> None:
        render.open()
        render.start()
        failure = OSError("no room on the device")

        render.service.emit(ServiceError(exception=failure))
        render.advance_frame()

        assert render.dialogs.errors == [
            {
                "exception": failure,
                "message": "settings.render.message.render_failed",
            }
        ]

    def test_a_stopped_render_closes_without_a_report(self, render: RenderFixture) -> None:
        render.open()
        render.start()
        render.stop()

        render.service.emit(ServiceCancelled())
        render.advance_frame()

        assert render.window.hides == 1
        assert not render.dialogs.paths
        assert not render.dialogs.errors

    @pytest.mark.parametrize(
        "outcome",
        [
            ServiceSuccess(value=CHOSEN),
            ServiceError(exception=OSError("no room on the device")),
            ServiceCancelled(),
        ],
        ids=["completed", "failed", "cancelled"],
    )
    def test_every_outcome_hands_the_application_back(
        self,
        render: RenderFixture,
        outcome: Any,
    ) -> None:
        render.open()
        render.start()

        render.service.emit(outcome)

        assert not render.coordinator.is_active
        assert not render.window.visible
