from pydantic import BaseModel


class SchedulingEmit(BaseModel, extra="forbid", frozen=True):
    priority: int
    batch_size: int
