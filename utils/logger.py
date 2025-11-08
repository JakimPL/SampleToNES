import logging
import sys
import traceback
from typing import Optional


class Logger:
    _instance: Optional["Logger"] = None
    _logger: logging.Logger

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._logger = logging.getLogger("SampleToNES")
            self._logger.setLevel(logging.DEBUG)

            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)

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

    def error_with_traceback(self, message: str, exception: Optional[Exception] = None) -> None:
        if exception:
            tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
            self._logger.error(f"{message}\n{tb}")
        else:
            tb = "".join(traceback.format_stack())
            self._logger.error(f"{message}\n{tb}")

    def critical(self, message: str) -> None:
        self._logger.critical(message)


logger = Logger()
