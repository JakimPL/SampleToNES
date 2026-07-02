import logging
from enum import StrEnum
from pathlib import Path
from typing import Dict, Final

from pydantic import BaseModel

from sampletones_shared.utils.serialization import load_yaml


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def to_logging_level(self) -> int:
        return _LOGGING_LEVELS[self]


_LOGGING_LEVELS: Final[Dict[LogLevel, int]] = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
    LogLevel.CRITICAL: logging.CRITICAL,
}

DEFAULT_LOG_LEVEL: Final[LogLevel] = LogLevel.INFO
DEFAULT_STRICT_HISTORY: Final[bool] = False


class DeploymentConfig(BaseModel, frozen=True):
    """Environment-level knobs decided at deployment time, not by the end user.

    ``strict_history`` turns an untracked domain mutation into an immediate
    ``UntrackedMutationError`` so development and test builds surface completeness
    gaps at once; production builds leave it off and let the history self-heal.
    ``log_level`` sets the verbosity of the application logger at startup.

    Every field is required: the shipped YAML is the authoritative source, so the
    model declares no defaults for the loader to silently fall back on.
    """

    log_level: LogLevel
    strict_history: bool


def load_deployment_config(deployment_path: Path) -> DeploymentConfig:
    raw = load_yaml(deployment_path)
    if not isinstance(raw, dict):
        raise TypeError(f"Deployment config file {deployment_path} must contain a mapping, got {type(raw)}")

    return DeploymentConfig.model_validate(raw)
