from pydantic import BaseModel


class SchedulingDelays(BaseModel, extra="forbid", frozen=True):
    schedule: int
    reconstruction_update: int
    cancel: int


class SchedulingPriorities(BaseModel, extra="forbid", frozen=True):
    update_status: int
    gui_action: int
    schedule: int


class SchedulingEmit(BaseModel, extra="forbid", frozen=True):
    priority: int
    batch_size: int


class SchedulingBehavior(BaseModel, extra="forbid", frozen=True):
    delays: SchedulingDelays
    priorities: SchedulingPriorities
    emit: SchedulingEmit
    queue_budget_seconds: float


class UiBehavior(BaseModel, extra="forbid", frozen=True):
    status_bar_display_time: float


class MainBehavior(BaseModel, extra="forbid", frozen=True):
    fps_update_interval: float
    max_workers_minimum: int


class BehaviorConfig(BaseModel, extra="forbid", frozen=True):
    scheduling: SchedulingBehavior
    ui: UiBehavior
    main: MainBehavior
