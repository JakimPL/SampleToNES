from pydantic import BaseModel


class GraphRange(BaseModel, extra="forbid", frozen=True):
    min_x: float
    max_x: float
    min_y: float
    max_y: float
