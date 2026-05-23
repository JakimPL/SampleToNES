from __future__ import annotations

import logging
from typing import Optional

from sampletones.meta import SingletonMeta


class NullLogger(metaclass=SingletonMeta):
    def __init__(self, level: int = logging.INFO) -> None:
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
