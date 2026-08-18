from pydantic import BaseModel


class SchedulingDelays(BaseModel, extra="forbid", frozen=True):
    schedule: int
    reconstruction_update: int
    cancel: int
