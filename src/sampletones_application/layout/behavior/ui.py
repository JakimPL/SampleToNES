from pydantic import BaseModel


class UIBehavior(BaseModel, extra="forbid", frozen=True):
    status_bar_display_time: float
    fps_update_interval: float
