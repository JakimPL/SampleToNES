from pydantic import BaseModel


class SchedulingPriorities(BaseModel, extra="forbid", frozen=True):
    update_status: int
    gui_action: int
    schedule: int
