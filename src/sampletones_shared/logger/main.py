from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from rich.logging import RichHandler

from sampletones_shared.application import SAMPLETONES_NAME
from sampletones_shared.meta import SingletonMeta
from sampletones_shared.types.path import Pathlike


class Logger(metaclass=SingletonMeta):
    """The application-wide logger, backed by a Rich console handler.

    A single instance serves the whole process (through :class:`SingletonMeta`) and
    writes formatted, coloured records to the terminal. The severity methods
    ``debug``, ``info``, ``warning``, ``error``, and ``critical`` each forward a
    message to the underlying :mod:`logging` logger at that level.
    """

    _logger: logging.Logger

    def __init__(self, level: int = logging.DEBUG) -> None:
        self._logger = logging.getLogger(SAMPLETONES_NAME)
        self._logger.setLevel(level)

        handler = RichHandler(
            markup=True,
            show_time=False,
            show_level=True,
            show_path=False,
            rich_tracebacks=False,
        )
        handler.setLevel(level)
        self._logger.addHandler(handler)

    def set_level(self, level: int) -> None:
        """Sets the logging threshold on the logger and each of its handlers.

        Args:
            level (int): A :mod:`logging` level such as ``logging.DEBUG``.
        """
        self._logger.setLevel(level)
        for handler in self._logger.handlers:
            handler.setLevel(level)

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

    def error_with_traceback(
        self,
        exception: BaseException,
        message: Optional[str] = None,
    ) -> None:
        """Logs an error with the exception's traceback and stack attached.

        Args:
            exception (BaseException): The exception whose traceback is recorded.
            message (Optional[str]): Text to log. Defaults to the exception's type name.
        """
        if not message:
            message = f"{type(exception).__name__}"
        self._logger.error(message, exc_info=exception, stack_info=True)

    def format_path(self, filepath: Pathlike) -> str:
        """Formats a filesystem path as a clickable terminal hyperlink.

        Args:
            filepath (Pathlike): The path to render.

        Returns:
            str: Rich ``[link=...]`` markup that opens the file's location.
        """
        path = Path(filepath).absolute()
        encoded_path = quote(str(path))
        return f'[link=file://{encoded_path}]"{filepath}"[/link]'
