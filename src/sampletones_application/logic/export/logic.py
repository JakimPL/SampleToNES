from typing import Callable, Dict, Final, List, Optional

from sampletones_application.services.export.result import (
    ExportError,
    ExportResult,
    ExportSuccess,
)
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceProgress,
    ServiceStarted,
)
from sampletones_application.view_model.shared.export import (
    NO_PROGRESS,
    NOTHING_MEASURED,
    ExportPhase,
    SongExportViewModel,
)
from sampletones_core.exports.stage import TRAVELLING_STAGES, ExportStage
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

from .protocol import ExportProgressServiceProtocol

NO_FIGURE: Final[str] = ""


class SongExportLogic(CallbackMixin):
    """Owns what a running export looks like to the reader: which stages it has reached, and
    where the one under way stands.

    A format states its own stages as it reaches them, so the run's shape is learned rather than
    declared: a tracker instrument reports one stage and a console program three. What the stage
    under way has covered is read in the unit that stage counts in — a fraction where it arrives
    at an end, and the bytes against the room there is where it does not.

    An export holds the application while it writes, so the dialog stands from the first word the
    run says until the outcome that ends it, and cancelling is answered at the next point the
    format looks up.
    """

    def __init__(
        self,
        export_service: ExportProgressServiceProtocol,
        *,
        stage_labels: Dict[ExportStage, str],
        size_template: str,
        cancelling_label: str,
    ) -> None:
        self._service = export_service
        self._stage_labels = stage_labels
        self._size_template = size_template
        self._cancelling_label = cancelling_label

        self._phase: ExportPhase = ExportPhase.IDLE
        self._stages: List[ExportStage] = []
        self._figure: str = NO_FIGURE
        self._progress: float = NO_PROGRESS
        self._travelling: bool = False

        self._service.subscribe(self._on_service_result)

        self.on_view_changed: Optional[Callable[[SongExportViewModel], None]] = None
        self.on_started: Optional[VoidCallback] = None
        self.on_finished: Optional[VoidCallback] = None

    @property
    def is_active(self) -> bool:
        """An export holds the dialog from its first word until the outcome that ends it."""
        return self._phase != ExportPhase.IDLE

    def stage_label(self, stage: ExportStage) -> str:
        """What the reader knows ``stage`` by."""
        return self._stage_labels[stage]

    def cancel(self) -> None:
        """Asks a running export to stop at the next point the format looks up."""
        if not self._service.is_running():
            return

        self._phase = ExportPhase.CANCELLING
        self._figure = self._cancelling_label
        self._travelling = False
        self._emit_view()
        self._service.cancel()

    def cleanup(self) -> None:
        """Winds a running export down for application exit."""
        self._service.shutdown()

    def _on_service_result(self, result: ExportResult) -> None:
        match result:
            case ServiceStarted():
                self._on_started()
            case ServiceProgress() as progress:
                self._on_progress(progress)
            case ExportSuccess() | ExportError() | ServiceCancelled():
                self._on_finished()

    def _on_started(self) -> None:
        self._phase = ExportPhase.EXPORTING
        self._stages = []
        self._figure = NO_FIGURE
        self._progress = NO_PROGRESS
        self._travelling = True
        self._emit_view()
        self.call(self.on_started)

    def _on_progress(self, progress: ServiceProgress[ExportStage]) -> None:
        """Puts the stage's own reading on screen, holding what a stop was asked under."""
        if self._phase == ExportPhase.CANCELLING:
            return

        stage = progress.current_item
        if stage is None:
            return

        self._reach(stage)
        self._travelling = stage in TRAVELLING_STAGES
        self._progress = self._fraction(progress)
        self._figure = self._figure_text(progress)
        self._emit_view()

    def _reach(self, stage: ExportStage) -> None:
        if stage not in self._stages:
            self._stages.append(stage)

    def _fraction(self, progress: ServiceProgress[ExportStage]) -> float:
        if progress.total <= NOTHING_MEASURED:
            return NO_PROGRESS

        return progress.completed / progress.total

    def _figure_text(self, progress: ServiceProgress[ExportStage]) -> str:
        """What the stage under way has covered, stated where the stage travels toward no end.

        A stage arriving at an end carries its own bar and the percentage written over it, so the
        figure is spelled out for the one that does not: what the song takes so far against what
        the console has room for, which is the answer the reader is waiting on.
        """
        if self._travelling or progress.total <= NOTHING_MEASURED:
            return NO_FIGURE

        return self._size_template.format(
            completed=progress.completed,
            total=progress.total,
        )

    def _on_finished(self) -> None:
        self._phase = ExportPhase.IDLE
        self._emit_view()
        self.call(self.on_finished)

    def _emit_view(self) -> None:
        self.call(self.on_view_changed, self._view_model())

    def _view_model(self) -> SongExportViewModel:
        return SongExportViewModel(
            phase=self._phase,
            stages=tuple(self._stages),
            figure=self._figure,
            progress=self._progress,
            travelling=self._travelling,
        )
