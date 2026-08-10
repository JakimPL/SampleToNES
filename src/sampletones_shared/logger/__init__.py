from .base import LoggerProtocol
from .main import Logger
from .null import NullLogger

logger = Logger()
null_logger = NullLogger()

__all__ = [
    "Logger",
    "LoggerProtocol",
    "NullLogger",
    "logger",
    "null_logger",
]
