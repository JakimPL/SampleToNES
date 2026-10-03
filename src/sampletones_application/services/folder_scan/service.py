import threading
from functools import partial
from pathlib import Path
from typing import Final, List, Optional

from sampletones_application.services.base import ServiceBase
from sampletones_application.services.folder_scan.result import (
    FolderScanCanceled,
    FolderScanError,
    FolderScanProgress,
    FolderScanRequest,
    FolderScanResult,
    FolderScanStarted,
    FolderScanSuccess,
)
from sampletones_application.utils.parallelization.thread import BackgroundWorkCanceled, SingleThreadExecutor
from sampletones_core.reconstructions.converter.paths import walk_entries
from sampletones_shared.paths.extensions import is_audio_file

REPORT_EVERY: Final[int] = 64
REPORT_DUE: Final[int] = 0


class FolderScanService(ServiceBase[FolderScanResult]):
    """Reads the recordings below a folder beside the interface, counting them as it goes.

    A folder a reader points at holds a handful of recordings or a disk's worth, and finding out
    costs what the tree costs, which is seconds where the tree is large. The walk runs on a worker
    of its own and reports how many recordings it has met. It gives up at the next entry it meets
    once the reader stops it, and once the application shuts down, so a walk ends with the run.
    Every report names the request it answers.
    """

    def __init__(self, priority: int) -> None:
        super().__init__(priority)
        self._executor = SingleThreadExecutor()
        self._stopping = threading.Event()

    def start(self, request: FolderScanRequest) -> None:
        """Reads the folder ``request`` names on the worker.

        One reading runs at a time, so a reading started as the last one unwinds waits for it to end.
        Each reading listens for a Stop of its own.
        """
        stopping = threading.Event()
        self._stopping = stopping
        self._executor.execute(partial(self._run, request, stopping), wait=True)

    def stop(self) -> None:
        """Asks the latest reading to give up, which it does at the next entry it meets."""
        self._stopping.set()

    def _run(self, request: FolderScanRequest, stopping: threading.Event) -> None:
        """Reads the folder and reports how the reading ended.

        A shutdown ends the reading with no report, since nothing is left to hear it.
        """
        if SingleThreadExecutor.is_shutting_down():
            return

        self._emit(FolderScanStarted(request=request))
        try:
            recordings = self._gather(request, stopping)
        except BackgroundWorkCanceled:
            return
        except Exception as exception:  # pylint: disable=broad-exception-caught
            self._emit(FolderScanError(request=request, exception=exception))
            return

        if recordings is None:
            self._emit(FolderScanCanceled(request=request))
            return

        self._emit(FolderScanSuccess(request=request, recordings=tuple(sorted(recordings))))

    def _gather(self, request: FolderScanRequest, stopping: threading.Event) -> Optional[List[Path]]:
        """The recordings met below the folder, or ``None`` where the reader stopped the walk.

        Every entry the tree holds is offered, so a folder of thousands holding a handful of
        recordings answers Stop and a shutdown as promptly as one holding thousands.

        Raises:
            BackgroundWorkCanceled: If the application shuts down while the walk runs.
        """
        found: List[Path] = []
        for path in walk_entries(request.root):
            if SingleThreadExecutor.is_shutting_down():
                raise BackgroundWorkCanceled

            if stopping.is_set():
                return None

            if not is_audio_file(path):
                continue

            found.append(path)
            if len(found) % REPORT_EVERY == REPORT_DUE:
                self._emit(FolderScanProgress(request=request, count=len(found)))

        return found
