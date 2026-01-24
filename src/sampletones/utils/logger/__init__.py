from .base import BaseLogger
from .main import Logger
from .null import NullLogger

logger = Logger()
null_logger = NullLogger()

__all__ = [
    "logger",
    "null_logger",
    "Logger",
    "NullLogger",
    "BaseLogger",
]
