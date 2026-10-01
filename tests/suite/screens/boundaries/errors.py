import logging
import threading
from typing import List, Tuple

from sampletones_shared.application import SAMPLETONES_NAME


class ErrorRecords(logging.Handler):
    """Every error the application logs, and every exception one of its threads lets escape.

    A gesture's callback that raises is logged and swallowed so the interface keeps running, which
    is why a scenario reads this record: a click that failed this way leaves the screen looking calm.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self._messages: List[str] = []
        self._lock = threading.Lock()

    def install(self) -> None:
        logging.getLogger(SAMPLETONES_NAME).addHandler(self)
        threading.excepthook = self._escaped

    @property
    def messages(self) -> Tuple[str, ...]:
        with self._lock:
            return tuple(self._messages)

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.ERROR:
            return

        self._record(self.format(record))

    def _escaped(self, arguments: threading.ExceptHookArgs) -> None:
        thread = arguments.thread.name if arguments.thread is not None else "a thread"
        self._record(f"{thread} let {arguments.exc_type.__name__} escape: {arguments.exc_value}")

    def _record(self, message: str) -> None:
        with self._lock:
            self._messages.append(message)
