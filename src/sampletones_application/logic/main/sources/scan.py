from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional, Protocol, Tuple

from sampletones_application.services.folder_scan.result import (
    FolderScanCanceled,
    FolderScanError,
    FolderScanProgress,
    FolderScanRequest,
    FolderScanResult,
    FolderScanStarted,
    FolderScanSuccess,
)
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

CountCallback = Callable[[int], None]
FailureCallback = Callable[[Exception], None]
FoundCallback = Callable[[Path, Tuple[Path, ...]], None]


class FolderScanServiceProtocol(Protocol):
    """The calls a folder scan makes of the service that walks the tree."""

    def subscribe(self, handler: Callable[[FolderScanResult], None]) -> None: ...

    def start(self, request: FolderScanRequest) -> None: ...

    def stop(self) -> None: ...


class ScanPhase(Enum):
    """Where the reading of a folder stands, from the reader's request until the walk lets it go."""

    IDLE = auto()
    READING = auto()
    WINDING_DOWN = auto()


@dataclass(frozen=True)
class AskedFolder:
    """A folder asked to be read, and what hears its recordings once it is."""

    root: Path
    answer: FoundCallback


class FolderScan(CallbackMixin):
    """The reading of a folder a reader points at, from the moment it is asked for until it is let go.

    A reading is idle, reading, or winding down. Stop ends the reading for the reader at once, while
    the walk runs on to the next entry it meets, so the scan winds down until the walk is heard to
    give up. A folder asked for in that span is read as soon as it has, the latest one asked for
    taking the place of an earlier one. A folder asked for while another is being read is turned
    away.

    The reports arrive on the render thread through the service, each naming the request it
    answers, so a report of a reading already let go is set aside.
    """

    def __init__(self, service: FolderScanServiceProtocol) -> None:
        self._service = service
        self._phase: ScanPhase = ScanPhase.IDLE
        self._reading: Optional[FolderScanRequest] = None
        self._answer: Optional[FoundCallback] = None
        self._next: Optional[AskedFolder] = None

        self.on_started: Optional[PathCallback] = None
        self.on_progress: Optional[CountCallback] = None
        self.on_stopped: Optional[VoidCallback] = None
        self.on_failed: Optional[FailureCallback] = None

        service.subscribe(self._on_result)

    @property
    def phase(self) -> ScanPhase:
        return self._phase

    def start(self, root: Path, answer: FoundCallback) -> None:
        """Reads what ``root`` holds and hands it to ``answer``, counting as the walk goes.

        The answer travels with the reading that earns it, so the same scan serves a gathering and
        a conversion and each hears back from its own reading. One reading runs at a time: a folder
        asked for while another is being read is turned away, and one asked for once Stop has closed
        the window is read as soon as the stopped walk has given up.
        """
        match self._phase:
            case ScanPhase.IDLE:
                self._begin(AskedFolder(root=root, answer=answer))
            case ScanPhase.READING:
                return
            case ScanPhase.WINDING_DOWN:
                self._next = AskedFolder(root=root, answer=answer)

    def stop(self) -> None:
        """Gives the reading up for the reader, which the walk hears at the next entry it meets."""
        if self._phase is not ScanPhase.READING:
            return

        self._phase = ScanPhase.WINDING_DOWN
        self._service.stop()

    def _begin(self, asked: AskedFolder) -> None:
        request = FolderScanRequest(root=asked.root)
        self._phase = ScanPhase.READING
        self._reading = request
        self._answer = asked.answer
        self._service.start(request)

    def _on_result(self, result: FolderScanResult) -> None:
        if result.request is not self._reading:
            return

        match result:
            case FolderScanStarted(request=request):
                self._report_started(request.root)
            case FolderScanProgress(count=count):
                self._report_progress(count)
            case FolderScanSuccess(request=request, recordings=recordings):
                self._land_found(request.root, recordings)
            case FolderScanCanceled():
                self._land_stopped()
            case FolderScanError(exception=exception):
                self._land_failed(exception)

    def _report_started(self, root: Path) -> None:
        if self._phase is ScanPhase.READING:
            self.call(self.on_started, root)

    def _report_progress(self, count: int) -> None:
        if self._phase is ScanPhase.READING:
            self.call(self.on_progress, count)

    def _land_found(self, root: Path, recordings: Tuple[Path, ...]) -> None:
        """Hands the recordings to whoever asked, where the reader still waits for them.

        A walk that reached the end of its tree before it heard Stop answers a reader who gave it
        up, so it ends the way a stopped one does.
        """
        if self._phase is ScanPhase.WINDING_DOWN:
            self._land_stopped()
            return

        answer = self._answer
        self._settle()
        self.call(answer, root, recordings)

    def _land_stopped(self) -> None:
        self._settle()
        self.call(self.on_stopped)
        self._read_next()

    def _land_failed(self, exception: Exception) -> None:
        """Reports a reading that failed partway, and goes on to the folder asked for meanwhile."""
        reading = self._phase is ScanPhase.READING
        self._settle()
        if reading:
            self.call(self.on_failed, exception)
        else:
            self.call(self.on_stopped)

        self._read_next()

    def _settle(self) -> None:
        self._phase = ScanPhase.IDLE
        self._reading = None
        self._answer = None

    def _read_next(self) -> None:
        asked = self._next
        self._next = None
        if asked is not None:
            self._begin(asked)
