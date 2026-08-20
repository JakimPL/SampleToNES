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
from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_shared.logger import logger

NO_EXPORT_FORMAT: None = None


class ExportService(ServiceBase[ExportResult]):
    """Writes exports on a background thread and reports each outcome as a result.

    The export backend arrives per call, so the service stays free of any one file
    format: it owns the thread boundary and the error boundary, and the backend owns
    what lands on disk. Each result names the format it was written in, letting one
    subscriber report an outcome in the words of the program that reads it.
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
                        export_format=NO_EXPORT_FORMAT,
                        truncation=None,
                    )
                )
            except Exception as exception:  # pylint: disable=broad-exception-caught
                logger.error_with_traceback(exception, f"Failed to export reconstruction to WAV: {filepath}")
                self._emit(
                    ExportError(
                        kind=ExportKind.WAV,
                        export_format=NO_EXPORT_FORMAT,
                        exception=exception,
                    )
                )

        self._executor.execute(task, wait=False)

    def export_instrument(
        self,
        destination: Path,
        backend: ExportBackend,
        request: InstrumentExport,
    ) -> None:
        self._submit(
            ExportKind.INSTRUMENT,
            destination,
            backend.export_format,
            partial(backend.write_instrument, destination, request),
        )

    def export_sample(
        self,
        destination: Path,
        backend: ExportBackend,
        request: SampleExport,
    ) -> None:
        self._submit(
            ExportKind.SAMPLE,
            destination,
            backend.export_format,
            partial(backend.write_sample, destination, request),
        )

    def export_project(
        self,
        destination: Path,
        backend: ExportBackend,
        request: ProjectExport,
    ) -> None:
        self._submit(
            ExportKind.PROJECT,
            destination,
            backend.export_format,
            partial(backend.write_project, destination, request),
        )

    def _submit(
        self,
        kind: ExportKind,
        destination: Path,
        export_format: ExportFormat,
        write: Callable[[], ExportArtifact],
    ) -> None:
        """Runs one backend write on the executor and reports what it produced.

        The result reports a path the run actually wrote, so the dialog announcing it opens
        a file that is there: a batch naming its slices after the destination writes those
        slices rather than the destination itself.

        Args:
            kind: The artefact the run produces, naming the dialog that reports it.
            destination: The destination the run was given.
            export_format: The format the run writes, carried through to the result.
            write: Calls the backend and returns what it left on disk.
        """

        def task() -> None:
            try:
                artifact = write()
                for path in artifact.paths:
                    logger.info(f"Exported {kind.value}: {logger.format_path(path)}")

                self._emit(
                    ExportSuccess(
                        kind=kind,
                        filepath=artifact.paths[0] if artifact.paths else destination,
                        export_format=export_format,
                        truncation=artifact.truncation,
                    )
                )
            except Exception as exception:  # pylint: disable=broad-exception-caught
                logger.error_with_traceback(exception, f"Failed to export to: {destination}")
                self._emit(
                    ExportError(
                        kind=kind,
                        export_format=export_format,
                        exception=exception,
                    )
                )

        self._executor.execute(task, wait=False)
