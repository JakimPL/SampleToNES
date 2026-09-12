from pathlib import Path
from typing import Optional, Tuple

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.conversion.result import (
    ConversionItem,
    ConversionResult,
    ReconstructionStep,
)
from sampletones_application.services.result import (
    ServiceCanceled,
    ServiceError,
    ServiceIntermediate,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)
from sampletones_core.configs import Config
from sampletones_core.parallelization import ETAEstimator, TaskProgress, TaskStatus
from sampletones_core.parallelization.task import TaskStep
from sampletones_core.reconstructions.converter import ConversionPlan, ReconstructionConverter
from sampletones_core.reconstructions.stage import ReconstructionStage
from sampletones_shared.logger import logger
from sampletones_shared.utils.system.paths import to_path


class ConversionService(ServiceBase[ConversionResult]):
    """
    Translates raw ``ReconstructionConverter`` callbacks into a uniform result stream.

    This normalizes the impedance mismatch between the core converter's ad-hoc
    callback interface and the subscriber model used throughout the application.
    Library-generation progress is forwarded through the same stream so the
    converter panel has a single unified view.
    """

    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._converter: Optional[ReconstructionConverter] = None
        self._eta_estimator: Optional[ETAEstimator] = None

    def start(self, config: Config, plan: ConversionPlan) -> None:
        if self._converter is not None and self._converter.is_running():
            logger.warning("Conversion is already in progress")
            return

        self._converter = ReconstructionConverter(config=config, plan=plan)
        self._converter.set_callbacks(
            on_start=self._on_start,
            on_progress=self._on_progress,
            on_completed=self._on_completed,
            on_error=self._on_error,
            on_canceled=self._on_canceled,
        )
        self._converter.start()

    def cancel(self) -> None:
        if self._converter and self._converter.is_running():
            self._converter.cancel()

    def cleanup(self) -> None:
        if self._converter is not None:
            self._converter.cleanup()
            self._converter = None

        self._eta_estimator = None

    def shutdown(self) -> None:
        """Tears the converter's process pool down synchronously for application exit.

        The pool spawns its workers, so the process must reap them before it releases
        the shared resources they depend on; this blocks until the pool has stopped."""
        if self._converter is not None:
            self._converter.shutdown()
            self._converter = None

        self._eta_estimator = None

    def is_running(self) -> bool:
        return self._converter is not None and (
            self._converter.is_running() or self._converter.status == TaskStatus.PENDING
        )

    def _on_start(self) -> None:
        assert self._converter is not None
        total = self._converter.total_tasks
        self._eta_estimator = ETAEstimator(total=total)
        self._emit(ServiceStarted(total=total))

    def _on_progress(
        self,
        task_status: TaskStatus,
        task_progress: TaskProgress,
    ) -> None:
        match task_status:
            case TaskStatus.RUNNING | TaskStatus.CANCELING:
                self._emit(
                    ServiceProgress(
                        completed=task_progress.completed,
                        total=task_progress.total,
                        current_item=self._item(task_progress),
                        eta_seconds=self._estimate(task_progress),
                        partial=task_progress.partial,
                    )
                )
            case _:
                pass

    def _estimate(self, task_progress: TaskProgress) -> Optional[float]:
        """How long the run has left, read from the whole of what it has covered.

        The run's own reading counts the reconstruction under way, so an estimate taken from it
        moves while a single conversion runs rather than waiting for the file to be written.
        """
        if self._eta_estimator is None:
            return None

        return self._eta_estimator.update(task_progress.completed + task_progress.partial)

    @classmethod
    def _item(cls, task_progress: TaskProgress) -> Optional[ConversionItem]:
        """The reconstruction the run is building, where it has a recording to name.

        A run works on as many reconstructions as it has workers and names the one it has been at
        longest, whose step it carries; the reading a bar draws counts them all.
        """
        if task_progress.current_item is None:
            return None

        return ConversionItem(
            source=to_path(task_progress.current_item),
            step=cls._step(task_progress),
        )

    @staticmethod
    def _step(task_progress: TaskProgress) -> Optional[ReconstructionStep]:
        """What that reconstruction is doing, once it has said something about itself."""
        if not task_progress.steps:
            return None

        step: TaskStep = task_progress.steps[0]
        return ReconstructionStep(
            stage=ReconstructionStage(step.stage),
            completed=step.completed,
            total=step.total,
        )

    def _on_completed(self, written: Tuple[Path, ...]) -> None:
        self._emit(ServiceSuccess(value=written))

    def _on_error(self, exception: Exception) -> None:
        self._emit(ServiceError(exception=exception))

    def _on_canceled(self) -> None:
        self._emit(ServiceCanceled())

    def forward_library_progress(
        self,
        _status: TaskStatus,
        progress: TaskProgress,
    ) -> None:
        self._emit(ServiceIntermediate(data=progress))
