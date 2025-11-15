import logging
from typing import Optional

from .base import BaseLogger


class NullLogger(BaseLogger):
    _instance: Optional["NullLogger"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, level: int = logging.INFO):
        pass

    def debug(self, message: str) -> None:
        pass

    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass

    def critical(self, message: str) -> None:
        pass

    def error_with_traceback(self, exception: BaseException, message: Optional[str] = None) -> None:
        pass


null_logger = NullLogger()
