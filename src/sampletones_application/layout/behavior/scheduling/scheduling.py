from pydantic import BaseModel

from sampletones_application.layout.behavior.scheduling.delays import SchedulingDelays
from sampletones_application.layout.behavior.scheduling.emit import SchedulingEmit
from sampletones_application.layout.behavior.scheduling.priorities import SchedulingPriorities


class SchedulingBehavior(BaseModel, extra="forbid", frozen=True):
    delays: SchedulingDelays
    priorities: SchedulingPriorities
    emit: SchedulingEmit
    queue_budget_seconds: float
