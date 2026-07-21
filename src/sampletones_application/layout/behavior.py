from pydantic import BaseModel


class SchedulingBehavior(BaseModel, extra="forbid", frozen=True):
    delay_gui_action: int
    delay_schedule: int
    delay_reconstruction_update: int
    delay_cancel: int
    priority_update_status: int
    priority_gui_action: int
    priority_schedule: int
    priority_emit: int
    queue_budget_seconds: float
    emit_batch_size: int


class UiBehavior(BaseModel, extra="forbid", frozen=True):
    status_bar_display_time: float


class MainBehavior(BaseModel, extra="forbid", frozen=True):
    fps_update_interval: float
    max_workers_minimum: int


class BehaviorConfig(BaseModel, extra="forbid", frozen=True):
    scheduling: SchedulingBehavior
    ui: UiBehavior
    main: MainBehavior
