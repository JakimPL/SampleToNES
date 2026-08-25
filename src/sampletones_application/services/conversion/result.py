from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union

from sampletones_application.services.result import (
    ServiceCanceled,
    ServiceError,
    ServiceIntermediate,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)
from sampletones_core.parallelization import TaskProgress
from sampletones_core.reconstructions.stage import ReconstructionStage


@dataclass(frozen=True)
class ReconstructionStep:
    """What the reconstruction under way is doing, in the unit that work counts in.

    A conversion counts the files it writes, which for one recording — or one set of stems, since
    those are one reconstruction too — counts to one. The stage and its counts are the whole of
    what a reader watching a single conversion has to go on.
    """

    stage: ReconstructionStage
    completed: int
    total: int


@dataclass(frozen=True)
class ConversionItem:
    """The reconstruction a conversion is building, and what it is doing to build it.

    A run knows which recording it is reading from the moment it starts, and hears what that
    reconstruction is doing once the reconstruction has something to say, so the step arrives on
    an item that already names its source.
    """

    source: Path
    step: Optional[ReconstructionStep] = None


ConversionResult = Union[
    ServiceStarted,
    ServiceProgress[ConversionItem],
    ServiceIntermediate[TaskProgress],
    ServiceSuccess[Tuple[Path, ...]],
    ServiceError,
    ServiceCanceled,
]
