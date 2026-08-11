from enum import StrEnum
from pathlib import Path
from typing import Union

from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)


class RenderStage(StrEnum):
    """The pass a render is on, naming what a progress report is counting.

    Both passes count the samples the song holds, so a report reads the same way whichever one
    it comes from and a bar crosses the same axis twice.
    """

    SYNTHESIS = "synthesis"
    ENCODING = "encoding"


RenderResult = Union[
    ServiceStarted,
    ServiceProgress[RenderStage],
    ServiceSuccess[Path],
    ServiceError,
    ServiceCancelled,
]
