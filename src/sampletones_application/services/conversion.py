from pathlib import Path
from typing import Optional

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.result import (
    ConversionResult,
    ServiceCancelled,
    ServiceError,
    ServiceIntermediate,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)
from sampletones_core.configs import Config
from sampletones_core.parallelization import ETAEstimator, TaskProgress, TaskStatus
from sampletones_core.reconstructions.converter import ReconstructionConverter
from sampletones_shared.logger import logger
from sampletones_shared.utils.system.paths import to_path


class ConversionService(ServiceBase[ConversionResult]):
    """
    Translates raw ``ReconstructionConverter`` callbacks into a uniform result stream.

    This normalises the impedance mismatch between the core converter's ad-hoc
    callback interface and the subscriber model used throughout the application.
    Library-generation progress is forwarded through the same stream so the
    converter panel has a single unified view.
    """

    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._converter: Optional[ReconstructionConverter] = None
        self._eta_estimator: Optional[ETAEstimator] = None

    def start(self, config: Config, input_path: Path) -> None:
        if self._converter is not None and self._converter.is_running():
            logger.warning("Conversion is already in progress")
            return

        is_file = input_path.is_file()
        self._converter = ReconstructionConverter(
            config=config,
            input_path=input_path,
            is_file=is_file,
        )
        self._converter.set_callbacks(
            on_start=self._on_start,
            on_progress=self._on_progress,
            on_completed=self._on_completed,
            on_error=self._on_error,
            on_cancelled=self._on_cancelled,
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
        current_item: Optional[Path] = None
        if task_progress.current_item is not None:
            current_item = to_path(task_progress.current_item)

        match task_status:
            case TaskStatus.RUNNING | TaskStatus.CANCELLING:
                eta_seconds = self._eta_estimator.update(task_progress.completed) if self._eta_estimator else None
                self._emit(
                    ServiceProgress(
                        completed=task_progress.completed,
                        total=task_progress.total,
                        current_item=current_item,
                        eta_seconds=eta_seconds,
                    )
                )
            case _:
                pass

    def _on_completed(self, output_path: Path) -> None:
        self._emit(ServiceSuccess(value=output_path))

    def _on_error(self, exception: Exception) -> None:
        self._emit(ServiceError(exception=exception))

    def _on_cancelled(self) -> None:
        self._emit(ServiceCancelled())

    def forward_library_progress(
        self,
        _status: TaskStatus,
        progress: TaskProgress,
    ) -> None:
        self._emit(ServiceIntermediate(data=progress))
