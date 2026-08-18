from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.channels import ALL_CHANNELS
from sampletones_application.logic.sequencer.playback.synthesizer import (
    RowSynthesizer,
    SongLength,
)
from sampletones_application.logic.shared.project_source import ProjectSnapshot
from sampletones_application.services.render.result import RenderResult, RenderStage
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)
from sampletones_application.view_model.shared.render import (
    ACTIVE_PHASES,
    RenderPhase,
    SongRenderSettings,
    SongRenderViewModel,
)
from sampletones_core.audio.writers import (
    DEFAULT_AUDIO_FORMAT,
    AudioFormat,
    available_audio_formats,
    available_depths,
)
from sampletones_core.parallelization import ETAEstimator
from sampletones_shared.constants.project import DEFAULT_EXPORT_NAME
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.paths import get_filename, replace_suffix

from .protocol import SongRenderServiceProtocol


class SongRenderLogic(CallbackMixin):
    """Owns writing the open song to an audio file: what is written, where, and how far it has got.

    The song is rendered through the engine that plays it, over the document as it stood when the
    render was asked for, so a file describes one state of the project however the editing goes
    on. The rate is whatever the chosen format is written at, which the engine follows, so the
    tempo the groove states is the tempo the file holds.

    A render is an exclusive operation, held from the moment the dialog opens until it closes, so
    the phase alone reports whether the application is busy with one.
    """

    def __init__(
        self,
        project_controller: ProjectController,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        render_service: SongRenderServiceProtocol,
        *,
        language_manager: LanguageManager,
        is_operation_active: Callable[[], bool],
    ) -> None:
        self._project_controller = project_controller
        self._config_manager = config_manager
        self._session_manager = session_manager
        self._service = render_service
        self._is_operation_active = is_operation_active
        self._msg_cancelling = language_manager["settings.render.message.status_cancelling"]
        self._msg_cancelled = language_manager["settings.render.message.status_cancelled"]
        self._msg_completed = language_manager["settings.render.message.status_completed"]
        self._msg_failed = language_manager["settings.render.message.status_failed"]
        self._eta_template = language_manager["global.dialog.template.time_estimation"]
        self._stage_messages: Dict[RenderStage, str] = {
            RenderStage.SYNTHESIS: language_manager["settings.render.message.status_synthesis"],
            RenderStage.ENCODING: language_manager["settings.render.message.status_encoding"],
        }

        self._formats: Tuple[AudioFormat, ...] = available_audio_formats()
        self._settings = SongRenderSettings.initial(self._offered_format())
        self._phase: RenderPhase = RenderPhase.IDLE
        self._destination: Optional[Path] = None
        self._status_text: str = ""
        self._progress: float = 0.0

        self._service.subscribe(self._on_service_result)

        self.on_view_changed: Optional[Callable[[SongRenderViewModel], None]] = None
        self.on_choose_destination: Optional[Callable[[Path, AudioFormat], None]] = None
        self.on_success: Optional[PathCallback] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_cancelled: Optional[VoidCallback] = None

    @property
    def is_active(self) -> bool:
        """A render occupies the application from the dialog opening until it closes."""
        return self._phase in ACTIVE_PHASES

    def open(self) -> bool:
        """Offers the render settings for the open song, reporting whether the dialog took over.

        The destination is proposed afresh each time, so it carries the name the project is known
        by into the directory audio was last written to. This is where the exclusivity is claimed,
        which is why the busy authority is asked here and nowhere else along the way.
        """
        if self._is_operation_active():
            logger.warning("An exclusive operation is already in progress; the render was not offered")
            return False

        self._phase = RenderPhase.CONFIGURING
        self._destination = self._proposed_destination()
        self._status_text = ""
        self._progress = 0.0
        self._emit_view()
        return True

    def close(self) -> None:
        """Returns to idle once the dialog is done with, releasing the application."""
        self._phase = RenderPhase.IDLE
        self._progress = 0.0

    def apply(self, settings: SongRenderSettings) -> None:
        """Takes the choices the dialog stands at, renaming the destination after the format.

        Args:
            settings: The reconciled choices the dialog reports.
        """
        if self._phase != RenderPhase.CONFIGURING:
            return

        previous = self._settings.spec.extension
        self._settings = settings
        extension = settings.spec.extension
        if extension != previous:
            self._destination = replace_suffix(self._require_destination(), previous, extension)

        self._emit_view()

    def request_destination(self) -> None:
        """Asks for the file the render writes, starting from the one standing."""
        self.call(
            self.on_choose_destination,
            self._require_destination(),
            self._settings.spec.audio_format,
        )

    def set_destination(self, destination: Path) -> None:
        """Writes the render to ``destination``, remembering its directory for the next one."""
        self._destination = destination
        self._session_manager.set_audio_path(destination)
        self._emit_view()

    def start(self) -> None:
        """Renders the song to the chosen file, from its first row to its last.

        The kernel is built here, over a snapshot of the document and at the rate the chosen
        format is written at, so the worker reads a project that stands still while the editing
        carries on.
        """
        if self._phase != RenderPhase.CONFIGURING:
            return

        length = self._length()
        if length.samples <= 0:
            logger.warning("The song holds no rows to render")
            return

        started = self._service.start(
            synthesizer=self._build_synthesizer(),
            destination=self._require_destination(),
            spec=self._settings.spec,
            normalize=self._settings.normalize,
            total_samples=length.samples,
        )
        if not started:
            return

        self._phase = RenderPhase.RENDERING
        self._status_text = self._stage_messages[RenderStage.SYNTHESIS]
        self._progress = 0.0
        self._emit_view()

    def cancel(self) -> None:
        """Asks a running render to stop at its next row or block."""
        if not self._service.is_running():
            return

        self._phase = RenderPhase.CANCELLING
        self._status_text = self._msg_cancelling
        self._emit_view()
        self._service.cancel()

    def cleanup(self) -> None:
        """Winds a running render down for application exit."""
        self._service.shutdown()

    def _on_service_result(self, result: RenderResult) -> None:
        match result:
            case ServiceStarted():
                self._report(self._stage_messages[RenderStage.SYNTHESIS], 0.0)
            case ServiceProgress() as progress:
                self._handle_progress(progress)
            case ServiceSuccess(value=destination):
                self._on_render_complete(destination)
            case ServiceError(exception=exception):
                self._on_render_error(exception)
            case ServiceCancelled():
                self._on_cancellation_complete()

    def _handle_progress(self, progress: ServiceProgress[RenderStage]) -> None:
        """Puts a pass's report on the bar, holding the message a stop was asked under."""
        if self._phase == RenderPhase.CANCELLING:
            return

        self._phase = RenderPhase.RENDERING
        stage = progress.current_item
        status_text = self._status_text if stage is None else self._stage_status(stage, progress.eta_seconds)
        self._report(status_text, progress.completed / max(progress.total, 1))

    def _stage_status(self, stage: RenderStage, eta_seconds: Optional[float]) -> str:
        """What the pass is doing, and how long it has left where an estimate stands."""
        status_text = self._stage_messages[stage]
        eta_string = ETAEstimator.format_duration(eta_seconds)
        if eta_string:
            status_text += self._eta_template.format(eta_string=eta_string)

        return status_text

    def _on_render_complete(self, destination: Path) -> None:
        self._phase = RenderPhase.COMPLETED
        self._report(self._msg_completed, 1.0)
        self.call(self.on_success, destination)

    def _on_render_error(self, exception: Exception) -> None:
        self._phase = RenderPhase.FAILED
        self._report(self._msg_failed, 0.0)
        self.call(self.on_error, exception)

    def _on_cancellation_complete(self) -> None:
        self._phase = RenderPhase.CANCELLED
        self._report(self._msg_cancelled, 0.0)
        self.call(self.on_cancelled)

    def _report(self, status_text: str, progress: float) -> None:
        self._status_text = status_text
        self._progress = progress
        self._emit_view()

    def _build_synthesizer(self) -> RowSynthesizer:
        """The kernel a render runs on: the engine that plays the song, over a held document.

        Every channel sounds and the level stays at unity, since muting and the master gain are
        choices a listener makes about what reaches the speakers, while a render describes the
        document.
        """
        sample_rate = self._settings.spec.sample_rate
        return RowSynthesizer(
            ProjectSnapshot.capture(self._project_controller),
            self._config_manager.config.with_library(sample_rate=sample_rate),
            active_channels=lambda: ALL_CHANNELS,
            sample_rate=lambda: sample_rate,
        )

    def _length(self) -> SongLength:
        return SongLength.measure(
            self._project_controller.project,
            sample_rate=self._settings.spec.sample_rate,
        )

    def _offered_format(self) -> AudioFormat:
        """The container a dialog opens on: the usual one, or the first this installation writes."""
        if DEFAULT_AUDIO_FORMAT in self._formats:
            return DEFAULT_AUDIO_FORMAT

        return next(iter(self._formats), DEFAULT_AUDIO_FORMAT)

    def _proposed_destination(self) -> Path:
        """The file the dialog opens on: the project's name, where audio was last written."""
        name = self._project_controller.name or DEFAULT_EXPORT_NAME
        return self._session_manager.get_audio_path() / get_filename(name, self._settings.spec.extension)

    def _require_destination(self) -> Path:
        """The file the open dialog writes to.

        Raises:
            SystemError: when a render is driven while its dialog is closed.
        """
        if self._destination is None:
            raise SystemError("A render is set up only while its dialog is open")

        return self._destination

    def _emit_view(self) -> None:
        self.call(self.on_view_changed, self._build_view())

    def _build_view(self) -> SongRenderViewModel:
        return SongRenderViewModel(
            phase=self._phase,
            formats=self._formats,
            depths=available_depths(self._settings.spec.audio_format),
            settings=self._settings,
            destination=self._require_destination(),
            total_samples=self._length().samples,
            status_text=self._status_text,
            progress=self._progress,
        )
