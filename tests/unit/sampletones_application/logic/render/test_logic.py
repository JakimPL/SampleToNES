from pathlib import Path
from typing import Final, List
from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.render.logic import SongRenderLogic
from sampletones_application.logic.sequencer.playback.synthesizer import (
    RowSynthesizer,
    SongLength,
)
from sampletones_application.services.render.result import RenderStage
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceProgress,
    ServiceSuccess,
)
from sampletones_application.view_model.shared.render import (
    RenderPhase,
    SongRenderViewModel,
)
from sampletones_core.audio.writers import AudioFormat
from sampletones_core.configs import Config
from tests.suite.language import FakeLanguageManager
from tests.suite.render import FakeRenderService

AUDIO_DIRECTORY: Final[Path] = Path("/home/user/audio")
PROJECT_NAME: Final[str] = "chiptune"
LOW_RATE: Final[int] = 8000


class RenderFixture:
    """A render logic wired to a real project and a service that records what it is asked for."""

    def __init__(self, *, operation_active: bool = False, accepts: bool = True) -> None:
        project_manager = ProjectManager()
        project_manager.session.mark_loaded(PROJECT_NAME)
        self.controller = ProjectController(project_manager)
        self.session_manager = MagicMock()
        self.session_manager.get_audio_path.return_value = AUDIO_DIRECTORY
        self.service = FakeRenderService(accepts=accepts)
        self.views: List[SongRenderViewModel] = []
        self.logic = SongRenderLogic(
            self.controller,
            MagicMock(config=Config()),
            self.session_manager,
            self.service,
            language_manager=FakeLanguageManager(),  # type: ignore[arg-type]
            is_operation_active=lambda: operation_active,
        )
        self.logic.on_view_changed = self.views.append

    @property
    def view(self) -> SongRenderViewModel:
        assert self.views, "A view was expected to be emitted"
        return self.views[-1]

    def configure(self) -> None:
        self.logic.open()

    def start_at(self, sample_rate: int) -> None:
        self.configure()
        self.logic.apply(self.view.settings.with_sample_rate(sample_rate))
        self.logic.start()


@pytest.fixture
def render() -> RenderFixture:
    return RenderFixture()


def render_whole_song(synthesizer: RowSynthesizer) -> int:
    """The samples a kernel produces when the song is played from its first row to its last."""
    synthesizer.set_position(0, 0)
    synthesizer.reset()
    rendered = 0
    while not synthesizer.is_finished:
        chunk, _ = synthesizer.render_row()
        rendered += len(chunk)

    return rendered


class TestOfferingTheRender:
    def test_the_dialog_opens_on_a_destination_named_after_the_project(
        self,
        render: RenderFixture,
    ) -> None:
        render.configure()

        assert render.view.destination == AUDIO_DIRECTORY / f"{PROJECT_NAME}.wav"
        assert render.view.phase == RenderPhase.CONFIGURING

    def test_the_render_occupies_the_application_from_the_dialog_opening(
        self,
        render: RenderFixture,
    ) -> None:
        assert not render.logic.is_active

        render.configure()

        assert render.logic.is_active

    def test_another_exclusive_operation_holds_the_dialog_closed(self) -> None:
        render = RenderFixture(operation_active=True)

        assert not render.logic.open()
        assert not render.logic.is_active
        assert not render.views

    def test_closing_releases_the_application(self, render: RenderFixture) -> None:
        render.configure()

        render.logic.close()

        assert not render.logic.is_active


class TestTheDestinationFollowsTheFormat:
    def test_choosing_another_container_renames_the_file(self, render: RenderFixture) -> None:
        render.configure()

        render.logic.apply(render.view.settings.with_format(AudioFormat.MP3))

        assert render.view.destination == AUDIO_DIRECTORY / f"{PROJECT_NAME}.mp3"

    def test_a_chosen_destination_is_remembered_for_the_next_render(
        self,
        render: RenderFixture,
    ) -> None:
        render.configure()
        chosen = Path("/home/user/renders/take one.wav")

        render.logic.set_destination(chosen)

        assert render.view.destination == chosen
        render.session_manager.set_audio_path.assert_called_once_with(chosen)

    def test_the_destination_is_asked_for_from_where_it_stands(self, render: RenderFixture) -> None:
        render.configure()
        on_choose_destination = MagicMock()
        render.logic.on_choose_destination = on_choose_destination

        render.logic.request_destination()

        on_choose_destination.assert_called_once_with(
            AUDIO_DIRECTORY / f"{PROJECT_NAME}.wav",
            AudioFormat.WAVE,
        )


class TestStartingTheRender:
    def test_the_service_is_asked_for_the_chosen_file(self, render: RenderFixture) -> None:
        render.configure()
        render.logic.apply(render.view.settings.with_normalize(True))

        render.logic.start()

        request = render.service.request
        assert request.destination == render.view.destination
        assert request.spec == render.view.settings.spec
        assert request.normalize

    def test_the_song_is_measured_at_the_rate_it_is_written_at(self, render: RenderFixture) -> None:
        render.start_at(LOW_RATE)

        expected = SongLength.measure(render.controller.project, sample_rate=LOW_RATE)
        assert render.service.request.total_samples == expected.samples

    def test_the_kernel_renders_the_measured_song_over_a_held_document(
        self,
        render: RenderFixture,
    ) -> None:
        """The kernel reads a snapshot at the chosen rate, so the audio it produces is the length
        the service was told to expect however the project moves on."""
        render.start_at(LOW_RATE)
        request = render.service.request

        render.controller.set_tempo(render.controller.project.settings.tempo + 40)

        assert render_whole_song(request.synthesizer) == request.total_samples

    def test_a_declined_request_leaves_the_dialog_setting_up(self) -> None:
        render = RenderFixture(accepts=False)
        render.configure()

        render.logic.start()

        assert render.view.phase == RenderPhase.CONFIGURING

    def test_a_render_starts_from_the_setup_alone(self, render: RenderFixture) -> None:
        render.configure()
        render.logic.start()

        render.logic.start()

        assert len(render.service.requests) == 1


class TestReportingTheRender:
    def test_a_pass_reports_how_far_it_has_got(self, render: RenderFixture) -> None:
        render.configure()
        render.logic.start()

        render.service.emit(
            ServiceProgress(
                completed=25,
                total=100,
                current_item=RenderStage.SYNTHESIS,
            )
        )

        assert render.view.phase == RenderPhase.RENDERING
        assert render.view.progress == 0.25
        assert render.view.status_text.startswith("settings.render.message.status_synthesis")

    def test_the_second_pass_names_itself(self, render: RenderFixture) -> None:
        render.configure()
        render.logic.start()

        render.service.emit(
            ServiceProgress(
                completed=50,
                total=100,
                current_item=RenderStage.ENCODING,
            )
        )

        assert render.view.status_text.startswith("settings.render.message.status_encoding")

    def test_a_stop_holds_its_message_over_the_reports_still_arriving(
        self,
        render: RenderFixture,
    ) -> None:
        render.configure()
        render.logic.start()
        render.logic.cancel()

        render.service.emit(
            ServiceProgress(
                completed=75,
                total=100,
                current_item=RenderStage.SYNTHESIS,
            )
        )

        assert render.view.phase == RenderPhase.CANCELLING
        assert render.view.status_text == "settings.render.message.status_cancelling"

    def test_a_stop_reaches_the_service(self, render: RenderFixture) -> None:
        render.configure()
        render.logic.start()

        render.logic.cancel()

        assert render.service.cancels == 1

    def test_a_finished_render_reports_the_file_it_wrote(self, render: RenderFixture) -> None:
        render.configure()
        render.logic.start()
        on_success = MagicMock()
        render.logic.on_success = on_success
        written = AUDIO_DIRECTORY / f"{PROJECT_NAME}.wav"

        render.service.emit(ServiceSuccess(value=written))

        on_success.assert_called_once_with(written)
        assert render.view.phase == RenderPhase.COMPLETED
        assert render.view.progress == 1.0
        assert not render.logic.is_active

    def test_a_stopped_render_reports_the_cancellation(self, render: RenderFixture) -> None:
        render.configure()
        render.logic.start()
        on_cancelled = MagicMock()
        render.logic.on_cancelled = on_cancelled

        render.logic.cancel()
        render.service.emit(ServiceCancelled())

        on_cancelled.assert_called_once()
        assert render.view.phase == RenderPhase.CANCELLED
        assert not render.logic.is_active

    def test_a_failed_render_reports_what_went_wrong(self, render: RenderFixture) -> None:
        render.configure()
        render.logic.start()
        on_error = MagicMock()
        render.logic.on_error = on_error
        failure = OSError("no room on the device")

        render.service.emit(ServiceError(exception=failure))

        on_error.assert_called_once_with(failure)
        assert render.view.phase == RenderPhase.FAILED
        assert not render.logic.is_active

    def test_exit_winds_a_running_render_down(self, render: RenderFixture) -> None:
        render.configure()
        render.logic.start()

        render.logic.cleanup()

        assert render.service.shutdowns == 1
