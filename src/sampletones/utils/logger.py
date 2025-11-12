import logging
import sys
from typing import Optional


class Logger:
    _instance: Optional["Logger"] = None
    _logger: logging.Logger

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, level: int = logging.INFO):
        if not hasattr(self, "_initialized"):
            self._logger = logging.getLogger("SampleToNES")
            self._logger.setLevel(level)

            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)

            formatter = logging.Formatter("[%(levelname)s] %(message)s")
            handler.setFormatter(formatter)

            self._logger.addHandler(handler)
            self._initialized = True

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)

    def error_with_traceback(self, message: str, exception: Exception) -> None:
        self._logger.error(message, exc_info=exception, stack_info=True)

    def critical(self, message: str) -> None:
        self._logger.critical(message)


logger = Logger()
