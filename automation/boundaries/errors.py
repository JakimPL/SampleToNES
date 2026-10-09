import inspect
import logging
import threading
from dataclasses import dataclass
from types import CodeType
from typing import Final, List, Optional, Tuple

from sampletones_application.utils.parallelization.thread import (
    SingleThreadExecutor,
)
from sampletones_shared.application import SAMPLETONES_NAME

EXIT_JOIN_CODE: Final[CodeType] = SingleThreadExecutor.join_all.__code__


@dataclass
class _ErrorRecord:
    message: str
    claimed: bool


class ErrorRecords(logging.Handler):
    """Every error the application logs, and every exception one of its threads lets escape.

    A gesture's callback that raises is reported and the interface keeps running. The report is
    logged, and the error dialog shows it unless a report already stands, so this record holds every
    failure, the ones the screen shows once among them. The warning that background work outlived
    the exit's deadline counts as an error too, since the teardown destroys what that work still
    reaches.

    A scenario that provokes a failure claims the error it expects, and every error left unclaimed
    is one the application reported on its own.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self._records: List[_ErrorRecord] = []
        self._lock = threading.Lock()

    def install(self) -> None:
        """Starts recording what the application logs and what its threads let escape."""
        logging.getLogger(SAMPLETONES_NAME).addHandler(self)
        threading.excepthook = self._escaped

    @property
    def count(self) -> int:
        """How many errors have been recorded, claimed or not."""
        with self._lock:
            return len(self._records)

    def unclaimed(
        self,
        start: int,
        stop: Optional[int],
    ) -> Tuple[str, ...]:
        """The errors recorded from the ``start``-th up to the ``stop``-th, or on, that no scenario claimed."""
        with self._lock:
            return tuple(record.message for record in self._records[start:stop] if not record.claimed)

    def claim(self, naming: str) -> bool:
        """Takes the first unclaimed error whose message holds ``naming`` as provoked, and says whether one
        did.
        """
        with self._lock:
            for record in self._records:
                if not record.claimed and naming in record.message:
                    record.claimed = True
                    return True

        return False

    def emit(self, record: logging.LogRecord) -> None:
        """Records a logged error, and a warning logged from within the exit's join on background work."""
        if record.levelno < logging.ERROR and not _logged_by_the_exit_join():
            return

        self._record(f"{record.levelname} {self.format(record)}")

    def _escaped(self, arguments: threading.ExceptHookArgs) -> None:
        thread = arguments.thread.name if arguments.thread is not None else "a thread"
        self._record(f"{thread} let {arguments.exc_type.__name__} escape: {arguments.exc_value}")

    def _record(self, message: str) -> None:
        with self._lock:
            self._records.append(_ErrorRecord(message=message, claimed=False))


def _logged_by_the_exit_join() -> bool:
    """Whether the record being handled was logged from within the join that awaits background work.

    The application logs through a wrapper, so a record names the wrapper as its origin, and the
    call stack is what still holds the join.
    """
    frame = inspect.currentframe()
    while frame is not None:
        if frame.f_code is EXIT_JOIN_CODE:
            return True

        frame = frame.f_back

    return False
