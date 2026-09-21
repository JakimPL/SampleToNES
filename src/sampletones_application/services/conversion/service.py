from pathlib import Path
from typing import Optional, Tuple

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.conversion.result import (
    ConversionItem,
    ConversionResult,
    ReconstructionStep,
)
from sampletones_application.services.result import (
    NOTHING_UNDER_WAY,
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
        if self.is_running():
            logger.warning("Conversion is already in progress")
            return

        self.release()
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

    def release(self) -> None:
        """Ends the converter's run and lets the converter go once its pool has ended.

        A converter that has announced its outcome has already ended its pool, so this returns at
        once; a run still under way is canceled and its workers waited for, which is what the
        application's exit asks.
        """
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
                self._emit(self._reading(task_progress))
            case _:
                pass

    def _reading(self, task_progress: TaskProgress) -> ServiceProgress[ConversionItem]:
        """Where the run stands, counted in the unit the run's own size makes readable.

        A run writing one reconstruction counts to one, so the part of that reconstruction done is
        what a reader follows: the reading carries the stage the reconstruction is at, and the bar
        and the estimate move with it. A run writing several counts the reconstructions it has
        written, which is the unit a reader recognizes and the one the estimate is taken in, since
        such a run holds as many reconstructions under way at once as it has workers.
        """
        writes_one = task_progress.is_single
        under_way = task_progress.partial if writes_one else NOTHING_UNDER_WAY
        step = self._step(task_progress) if writes_one else None
        return ServiceProgress(
            completed=task_progress.completed,
            total=task_progress.total,
            current_item=self._item(task_progress, step),
            eta_seconds=self._estimate(task_progress.completed + under_way),
            partial=under_way,
        )

    def _estimate(self, covered: float) -> Optional[float]:
        """How long the run has left, read from what it has covered in the unit it counts in."""
        if self._eta_estimator is None:
            return None

        return self._eta_estimator.update(covered)

    @staticmethod
    def _item(
        task_progress: TaskProgress,
        step: Optional[ReconstructionStep],
    ) -> Optional[ConversionItem]:
        """The reconstruction the run names itself by, where it has a recording to name.

        A run works on as many reconstructions as it has workers and names the one it has been at
        longest, so a reader watching a batch sees the run move through its recordings.
        """
        if task_progress.current_item is None:
            return None

        return ConversionItem(source=to_path(task_progress.current_item), step=step)

    @staticmethod
    def _step(task_progress: TaskProgress) -> Optional[ReconstructionStep]:
        """What the reconstruction under way is doing, once it has said something about itself.

        A run writing one reconstruction holds one line open, so the step standing on it is that
        reconstruction's own.
        """
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
