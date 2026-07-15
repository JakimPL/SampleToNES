from pydantic import BaseModel


class SchedulingBehavior(BaseModel, extra="forbid", frozen=True):
    delay_gui_action: int
    delay_schedule: int
    delay_cancel: int
    priority_update_status: int
    priority_gui_action: int
    priority_schedule: int
    priority_add_handler: int
    priority_add_node: int
    queue_budget_seconds: float


class UiBehavior(BaseModel, extra="forbid", frozen=True):
    status_bar_display_time: float


class TreeBehavior(BaseModel, extra="forbid", frozen=True):
    priority_add_handler: int
    priority_add_node: int


class MainBehavior(BaseModel, extra="forbid", frozen=True):
    fps_update_interval: float
    max_workers_minimum: int
    explorer: TreeBehavior


class BehaviorConfig(BaseModel, extra="forbid", frozen=True):
    scheduling: SchedulingBehavior
    ui: UiBehavior
    main: MainBehavior
    instructions: TreeBehavior
    reconstructions: TreeBehavior
    sequencer: TreeBehavior
