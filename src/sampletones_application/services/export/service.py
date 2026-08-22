import threading
from functools import partial
from pathlib import Path
from typing import Callable, Final, Optional

import numpy as np

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.reporter import ExportProgressReporter
from sampletones_application.services.export.result import ExportResult
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.services.result import ServiceCancelled, ServiceStarted
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_core.audio import write_wave
from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.progress import ExportReporter
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_shared.exceptions import OperationCancelled
from sampletones_shared.logger import logger

NO_EXPORT_FORMAT: None = None
WHOLE_ENVELOPE: None = None
UNMEASURED_AT_THE_START: Final[int] = 0


class ExportService(ServiceBase[ExportResult]):
    """Writes exports on a background thread and reports each outcome as a result.

    The export backend arrives per call, so the service stays free of any one file
    format: it owns the thread boundary and the error boundary, and the backend owns
    what lands on disk. Each result names the format it was written in, letting one
    subscriber report an outcome in the words of the program that reads it.

    A format carrying its own player spends seconds on a song, so a run reports the stage it is
    in as it goes and answers a cancel at the next point the format looks up. One export runs at
    a time, and a request arriving while one is in flight is declined.
    """

    def __init__(self, priority: int = 0) -> None:
        super().__init__(priority)
        self._executor = SingleThreadExecutor()
        self._cancel_event = threading.Event()
        self._running = threading.Event()

    def cancel(self) -> None:
        """Asks a running export to stop at the next point the format looks up."""
        self._cancel_event.set()

    def is_running(self) -> bool:
        return self._running.is_set()

    def shutdown(self) -> None:
        """Winds a running export down for application exit.

        The worker runs on a :class:`SingleThreadExecutor`, so the teardown that joins every
        background worker reaches this one; asking it to stop first is what keeps that join short.
        """
        self._cancel_event.set()

    def export_wav(
        self,
        filepath: Path,
        sample_rate: int,
        audio: np.ndarray,
    ) -> None:
        """Writes the audio a reconstruction sounds as, straight to a file.

        Args:
            filepath: The file to write.
            sample_rate: The rate the samples were rendered at.
            audio: The samples to write.
        """
        self._submit(
            ExportKind.WAV,
            filepath,
            NO_EXPORT_FORMAT,
            partial(self._written_wave, filepath, sample_rate, audio),
        )

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

    def _written_wave(
        self,
        filepath: Path,
        sample_rate: int,
        audio: np.ndarray,
        _report: ExportReporter,
        /,
    ) -> ExportArtifact:
        """Writes the samples straight out, which takes a moment and reports no stages."""
        write_wave(filepath, sample_rate, audio)
        return ExportArtifact(paths=(filepath,), truncation=WHOLE_ENVELOPE)

    def _submit(
        self,
        kind: ExportKind,
        destination: Path,
        export_format: Optional[ExportFormat],
        write: Callable[[ExportReporter], ExportArtifact],
    ) -> None:
        """Runs one backend write on the executor and reports what it produced.

        The result reports a path the run actually wrote, so the dialog announcing it opens
        a file that is there: a batch naming its slices after the destination writes those
        slices rather than the destination itself.

        Args:
            kind: The artefact the run produces, naming the dialog that reports it.
            destination: The destination the run was given.
            export_format: The format the run writes, carried through to the result, and ``None``
                for an audio export.
            write: Calls the backend with the reporter it says its stages through, and returns
                what it left on disk.
        """
        if self.is_running():
            logger.warning(f"{self.class_name}: an export is already running; the request was declined")
            return

        self._cancel_event.clear()
        self._running.set()
        if not self._executor.execute(partial(self._run, kind, destination, export_format, write), wait=False):
            self._running.clear()

    def _run(
        self,
        kind: ExportKind,
        destination: Path,
        export_format: Optional[ExportFormat],
        write: Callable[[ExportReporter], ExportArtifact],
    ) -> None:
        try:
            self._emit(ServiceStarted(total=UNMEASURED_AT_THE_START))
            self._report_written(kind, destination, export_format, write(self._reporter()))
        except OperationCancelled:
            logger.info(f"The export to {logger.format_path(destination)} was cancelled")
            self._emit(ServiceCancelled())
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logger.error_with_traceback(exception, f"Failed to export to: {destination}")
            self._emit(
                ExportError(
                    kind=kind,
                    export_format=export_format,
                    exception=exception,
                )
            )
        finally:
            self._running.clear()

    def _report_written(
        self,
        kind: ExportKind,
        destination: Path,
        export_format: Optional[ExportFormat],
        artifact: ExportArtifact,
    ) -> None:
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

    def _reporter(self) -> ExportReporter:
        """What the backend says its stages through, and asks whether the run is still wanted."""
        return ExportProgressReporter(self._emit, self._cancel_event.is_set)
