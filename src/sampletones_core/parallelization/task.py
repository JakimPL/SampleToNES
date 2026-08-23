from enum import Enum
from typing import Final, Optional, Tuple

from pydantic import BaseModel, ConfigDict

NOTHING_TO_DO: Final[int] = 0


class TaskStatus(Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    CLEANING_UP = "CLEANING_UP"


class TaskStep(BaseModel):
    """How far one task of a run has come through work only it can see.

    A task that is the whole of what a run does leaves the run's own counts at nothing until it
    finishes, so a task that knows its way through its work says so here. The stage names the unit
    the counts are in, and the fraction is that stage read against the whole task, since the stages
    a task passes through count in units of their own.
    """

    model_config = ConfigDict(frozen=True)

    stage: str
    completed: int
    total: int
    fraction: float


class TaskReport(BaseModel):
    """One task's step, and which task of the run it came from."""

    model_config = ConfigDict(frozen=True)

    index: int
    step: TaskStep


class TaskProgress(BaseModel):
    """How far a run has come: the tasks it finished, and where the ones still running stand."""

    model_config = ConfigDict(frozen=True)

    total: int
    completed: int
    current_item: Optional[str] = None
    steps: Tuple[TaskStep, ...] = ()

    @property
    def partial(self) -> float:
        """The work under way beyond the finished tasks, counted in tasks."""
        return sum(step.fraction for step in self.steps)

    @property
    def fraction(self) -> float:
        """How full the run stands, each running task counted for the part of it that is done."""
        if self.total == NOTHING_TO_DO:
            return 0.0

        return (self.completed + self.partial) / self.total
