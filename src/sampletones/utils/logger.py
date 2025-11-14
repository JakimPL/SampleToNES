import logging
from typing import Optional

from rich.logging import RichHandler

from sampletones.constants.application import SAMPLETONES_NAME


class Logger:
    _instance: Optional["Logger"] = None
    _logger: logging.Logger

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, level: int = logging.INFO):
        if not hasattr(self, "_initialized"):
            self._logger = logging.getLogger(SAMPLETONES_NAME)
            self._logger.setLevel(level)

            handler = RichHandler(
                markup=False,
                show_time=False,
                show_level=True,
                show_path=False,
                rich_tracebacks=False,
            )
            handler.setLevel(level)
            self._handler = handler
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

    def critical(self, message: str) -> None:
        self._logger.critical(message)

    def error_with_traceback(self, exception: BaseException, message: Optional[str] = None) -> None:
        if not message:
            message = f"{str(type(exception).__name__)}"

        self._logger.error(message, exc_info=exception, stack_info=True)


logger = Logger()
