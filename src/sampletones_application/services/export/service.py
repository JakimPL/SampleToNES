from functools import partial
from pathlib import Path
from typing import Callable

import numpy as np

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.result import ExportResult
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_core.audio import write_wave
from sampletones_core.trackers.artifact import ExportArtifact
from sampletones_core.trackers.backend import TrackerBackend
from sampletones_core.trackers.request import InstrumentExport, SampleExport
from sampletones_shared.logger import logger


class ExportService(ServiceBase[ExportResult]):
    """Writes exports on a background thread and reports each outcome as a result.

    The tracker backend arrives per call, so the service stays free of any one file
    format: it owns the thread boundary and the error boundary, and the backend owns
    what lands on disk.
    """

    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._executor = SingleThreadExecutor()

    def export_wav(
        self,
        filepath: Path,
        sample_rate: int,
        audio: np.ndarray,
    ) -> None:
        def task() -> None:
            try:
                write_wave(filepath, sample_rate, audio)
                logger.info(f"Exported reconstruction to WAV: {logger.format_path(filepath)}")
                self._emit(
                    ExportSuccess(
                        kind=ExportKind.WAV,
                        filepath=filepath,
                        truncation=None,
                    )
                )
            except Exception as exception:  # pylint: disable=broad-exception-caught
                logger.error_with_traceback(exception, f"Failed to export reconstruction to WAV: {filepath}")
                self._emit(
                    ExportError(
                        kind=ExportKind.WAV,
                        exception=exception,
                    )
                )

        self._executor.execute(task, wait=False)

    def export_instrument(
        self,
        destination: Path,
        backend: TrackerBackend,
        request: InstrumentExport,
    ) -> None:
        self._submit(
            ExportKind.INSTRUMENT,
            destination,
            partial(backend.write_instrument, destination, request),
        )

    def export_sample(
        self,
        destination: Path,
        backend: TrackerBackend,
        request: SampleExport,
    ) -> None:
        self._submit(
            ExportKind.INSTRUMENTS,
            destination,
            partial(backend.write_sample, destination, request),
        )

    def _submit(
        self,
        kind: ExportKind,
        destination: Path,
        write: Callable[[], ExportArtifact],
    ) -> None:
        """Runs one backend write on the executor and reports what it produced.

        Args:
            kind: The artefact the run produces, naming the dialog that reports it.
            destination: The file written, or the directory a batch of instruments filled.
            write: Calls the backend and returns what it left on disk.
        """

        def task() -> None:
            try:
                artifact = write()
                for path in artifact.paths:
                    logger.info(f"Exported instrument: {logger.format_path(path)}")
                self._emit(
                    ExportSuccess(
                        kind=kind,
                        filepath=destination,
                        truncation=artifact.truncation,
                    )
                )
            except Exception as exception:  # pylint: disable=broad-exception-caught
                logger.error_with_traceback(exception, f"Failed to export to: {destination}")
                self._emit(
                    ExportError(
                        kind=kind,
                        exception=exception,
                    )
                )

        self._executor.execute(task, wait=False)
