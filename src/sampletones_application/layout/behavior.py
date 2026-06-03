from pydantic import BaseModel


class SchedulingBehavior(BaseModel, frozen=True):
    delay_gui_action: int
    delay_schedule: int
    delay_cancel: int
    priority_update_status: int
    priority_gui_action: int
    priority_schedule: int
    priority_add_handler: int
    priority_add_node: int


class UiBehavior(BaseModel, frozen=True):
    status_bar_display_time: float


class TreeBehavior(BaseModel, frozen=True):
    priority_add_handler: int
    priority_add_node: int


class MainBehavior(BaseModel, frozen=True):
    fps_update_interval: float
    max_workers_minimum: int
    explorer: TreeBehavior


class BehaviorConfig(BaseModel, frozen=True):
    scheduling: SchedulingBehavior
    ui: UiBehavior
    main: MainBehavior
    instructions: TreeBehavior
    reconstructions: TreeBehavior
    sequencer: TreeBehavior
