from pydantic import BaseModel


class SchedulingDelays(BaseModel, extra="forbid", frozen=True):
    schedule: int
    cancel: int
