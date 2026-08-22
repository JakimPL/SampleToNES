from typing import Union

from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceProgress,
    ServiceStarted,
)
from sampletones_core.exports.stage import ExportStage

ExportResult = Union[
    ServiceStarted,
    ServiceProgress[ExportStage],
    ExportSuccess,
    ExportError,
    ServiceCancelled,
]
