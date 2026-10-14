import logging
import threading
from typing import List

from sampletones_shared.application import SAMPLETONES_NAME


class ErrorLog(logging.Handler):
    """Every error the application logs while a case runs, from whichever thread logs it."""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self._lock_messages = threading.Lock()
        self._messages: List[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        with self._lock_messages:
            self._messages.append(f"{record.threadName}: {record.getMessage()}")

    @property
    def messages(self) -> List[str]:
        with self._lock_messages:
            return list(self._messages)

    def attach(self) -> None:
        logging.getLogger(SAMPLETONES_NAME).addHandler(self)

    def detach(self) -> None:
        logging.getLogger(SAMPLETONES_NAME).removeHandler(self)
