import threading
from pathlib import Path
from typing import Callable, Final, List, Optional, Tuple

from sampletones_application.utils.parallelization.thread import concurrent
from sampletones_core.reconstructions.converter.paths import walk_audio_files
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

CountCallback = Callable[[int], None]
FoundCallback = Callable[[Path, Tuple[Path, ...]], None]

REPORT_EVERY: Final[int] = 64
NOTHING_FOUND: Final[int] = 0


class FolderScan(CallbackMixin):
    """The recordings below a folder, read beside the interface rather than in front of it.

    A folder a reader points at holds a handful of recordings or a disk's worth, and finding out
    costs what the tree costs — seconds where the tree is large. The walk therefore runs on a
    worker, reports how many it has met as it goes, and stops when the reader asks it to, so the
    window keeps answering and the reader knows what it is waiting for.

    The reports arrive on the worker's own thread, so whoever draws from them crosses to the
    thread DearPyGui's context belongs to.
    """

    def __init__(self) -> None:
        self._stopping = threading.Event()
        self._running = threading.Event()

        self._answer: Optional[FoundCallback] = None

        self.on_started: Optional[PathCallback] = None
        self.on_progress: Optional[CountCallback] = None
        self.on_stopped: Optional[VoidCallback] = None

    @property
    def running(self) -> bool:
        """A walk is under way, which is what the reader is being shown."""
        return self._running.is_set()

    def start(self, root: Path, answer: FoundCallback) -> None:
        """Reads what ``root`` holds and hands it to ``answer``, counting as the walk goes.

        The answer belongs to the asking rather than to the scan, so the same walk serves a
        gathering and a conversion. A walk already under way stands, so a second folder waits for
        the one being read.
        """
        if self.running:
            return

        self._answer = answer
        self._stopping.clear()
        self._running.set()
        self.call(self.on_started, root)
        self._walk(root)

    def stop(self) -> None:
        """Asks the walk to give up, which it does at the next recording it meets."""
        self._stopping.set()

    @concurrent(wait=False)
    def _walk(self, root: Path) -> None:
        found: List[Path] = []
        for path in walk_audio_files(root):
            if self._stopping.is_set():
                self._settled(self.on_stopped)
                return

            found.append(path)
            if len(found) % REPORT_EVERY == NOTHING_FOUND:
                self.call(self.on_progress, len(found))

        self._running.clear()
        self.call(self._answer, root, tuple(sorted(found)))

    def _settled(self, report: Optional[VoidCallback]) -> None:
        """Lets the walk go and says how it ended, in that order, so a next one may start."""
        self._running.clear()
        self.call(report)
