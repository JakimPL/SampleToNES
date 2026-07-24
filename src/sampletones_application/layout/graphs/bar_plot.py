from pydantic import BaseModel


class BarPlotLayout(BaseModel, extra="forbid", frozen=True):
    min_x: float
    min_y: float
    max_y: float
    bar_weight: float
    hover_alpha: int
